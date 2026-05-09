"""Rule-based financial analyzer for producing AnalysisResult from FinancialMetrics."""

from typing import Optional

from tools.financial_reports.schemas import AnalysisResult, FinancialMetrics


class FinancialAnalyzer:
    """Rule-based analyzer that scores financial metrics and produces recommendations."""

    def analyze(
        self,
        stock_name: str,
        metrics_history: list[FinancialMetrics],
        raw_reports: list[str],
    ) -> AnalysisResult:
        """Analyze financial metrics and return an AnalysisResult."""
        if not metrics_history:
            return AnalysisResult(
                overall_health="未知",
                summary=f"未能提取{stock_name}的有效财务指标，无法进行分析。",
            )

        scores = self._calculate_scores(metrics_history)
        overall = self._overall_health(scores)
        risks = self._identify_risks(metrics_history)
        strengths = self._identify_strengths(metrics_history)
        concerns = self._identify_concerns(metrics_history)
        latest = metrics_history[-1]
        valuation = self._valuation_comment(latest)
        recommendation = self._recommendation(overall, risks)
        summary = self._generate_summary(
            stock_name, overall, scores, risks, strengths, concerns, valuation, recommendation
        )

        return AnalysisResult(
            overall_health=overall,
            risk_flags=risks,
            strengths=strengths,
            concerns=concerns,
            valuation_comment=valuation,
            recommendation=recommendation,
            summary=summary,
        )

    def _calculate_scores(self, metrics_history: list[FinancialMetrics]) -> dict[str, int]:
        """Calculate scores for ROE, margin, debt, and growth."""
        latest = metrics_history[-1]

        roe = latest.roe if latest.roe is not None else 0.0
        if roe >= 20:
            roe_score = 100
        elif roe >= 15:
            roe_score = 80
        elif roe >= 10:
            roe_score = 60
        elif roe >= 5:
            roe_score = 40
        else:
            roe_score = 20

        margin = latest.gross_margin if latest.gross_margin is not None else 0.0
        if margin >= 30:
            margin_score = 100
        elif margin >= 20:
            margin_score = 80
        elif margin >= 10:
            margin_score = 60
        elif margin >= 5:
            margin_score = 40
        else:
            margin_score = 20

        debt = latest.debt_ratio if latest.debt_ratio is not None else 0.0
        if debt <= 30:
            debt_score = 100
        elif debt <= 50:
            debt_score = 80
        elif debt <= 70:
            debt_score = 60
        else:
            debt_score = 40

        # Use revenue_yoy as growth proxy; fallback to net_profit_yoy
        growth = latest.revenue_yoy if latest.revenue_yoy is not None else 0.0
        if growth is None or growth == 0.0:
            growth = latest.net_profit_yoy if latest.net_profit_yoy is not None else 0.0
        if growth >= 30:
            growth_score = 100
        elif growth >= 15:
            growth_score = 80
        elif growth >= 5:
            growth_score = 60
        elif growth >= 0:
            growth_score = 40
        else:
            growth_score = 20

        return {
            "roe": roe_score,
            "margin": margin_score,
            "debt": debt_score,
            "growth": growth_score,
        }

    def _overall_health(self, scores: dict[str, int]) -> str:
        """Map aggregate scores to overall health rating."""
        avg = sum(scores.values()) / len(scores)
        if avg >= 80:
            return "优秀"
        elif avg >= 60:
            return "良好"
        elif avg >= 40:
            return "一般"
        else:
            return "差"

    def _identify_risks(self, metrics_history: list[FinancialMetrics]) -> list[str]:
        """Identify risk flags from metrics history."""
        risks: list[str] = []
        if not metrics_history:
            return risks
        latest = metrics_history[-1]

        if latest.debt_ratio is not None and latest.debt_ratio > 70:
            risks.append("负债率过高")
        if latest.operating_cash_flow is not None and latest.net_profit is not None:
            if latest.operating_cash_flow < latest.net_profit * 0.5:
                risks.append("经营现金流大幅低于净利润")
        if len(metrics_history) >= 2:
            prev = metrics_history[-2]
            if (
                prev.revenue is not None
                and latest.revenue is not None
                and prev.revenue > 0
                and latest.revenue < prev.revenue * 0.9
            ):
                risks.append("营收同比下滑明显")
            if (
                prev.net_profit is not None
                and latest.net_profit is not None
                and prev.net_profit > 0
                and latest.net_profit < prev.net_profit * 0.9
            ):
                risks.append("净利润同比下滑明显")

        return risks

    def _identify_strengths(self, metrics_history: list[FinancialMetrics]) -> list[str]:
        """Identify financial strengths."""
        strengths: list[str] = []
        if not metrics_history:
            return strengths
        latest = metrics_history[-1]

        if latest.roe is not None and latest.roe >= 15:
            strengths.append("净资产收益率优秀")
        if latest.gross_margin is not None and latest.gross_margin >= 30:
            strengths.append("毛利率水平较高")
        if latest.operating_cash_flow is not None and latest.net_profit is not None:
            if latest.operating_cash_flow >= latest.net_profit * 0.8:
                strengths.append("经营现金流健康")
        if latest.debt_ratio is not None and latest.debt_ratio <= 40:
            strengths.append("负债率较低，财务结构稳健")

        return strengths

    def _identify_concerns(self, metrics_history: list[FinancialMetrics]) -> list[str]:
        """Identify areas of concern."""
        concerns: list[str] = []
        if not metrics_history:
            return concerns
        latest = metrics_history[-1]

        if latest.roe is not None and latest.roe < 10:
            concerns.append("净资产收益率偏低")
        if latest.gross_margin is not None and latest.gross_margin < 20:
            concerns.append("毛利率水平偏低")
        if latest.net_margin is not None and latest.net_margin < 5:
            concerns.append("净利率偏低")
        if latest.debt_ratio is not None and 50 < latest.debt_ratio <= 70:
            concerns.append("负债率处于较高水平")

        return concerns

    def _valuation_comment(self, latest: FinancialMetrics) -> str:
        """Generate a valuation comment based on latest metrics."""
        # FinancialMetrics does not have pe/pb fields; derive a rough sense from margins/roe
        parts: list[str] = []
        if latest.roe is not None and latest.roe >= 20:
            parts.append("盈利能力强劲")
        if latest.gross_margin is not None and latest.gross_margin >= 50:
            parts.append("高毛利护城河")
        if latest.net_margin is not None and latest.net_margin >= 20:
            parts.append("净利率优秀")
        if not parts:
            return "缺乏估值数据，无法给出估值判断"
        return "，".join(parts)

    def _recommendation(self, overall: str, risks: list[str]) -> str:
        """Determine investment recommendation."""
        if overall == "优秀":
            return "买入"
        elif overall == "良好":
            return "持有" if len(risks) <= 1 else "观望"
        elif overall == "一般":
            return "观望"
        else:
            return "回避"

    def _generate_summary(
        self,
        stock_name: str,
        overall: str,
        scores: dict[str, int],
        risks: list[str],
        strengths: list[str],
        concerns: list[str],
        valuation: str,
        recommendation: str,
    ) -> str:
        """Generate a human-readable summary."""
        lines: list[str] = []
        lines.append(f"{stock_name}财务健康度评级：{overall}。")
        lines.append(
            f"核心指标得分——ROE:{scores['roe']} 毛利率:{scores['margin']} "
            f"负债:{scores['debt']} 成长性:{scores['growth']}。"
        )
        if strengths:
            lines.append(f"优势：{'、'.join(strengths)}。")
        if concerns:
            lines.append(f"关注点：{'、'.join(concerns)}。")
        if risks:
            lines.append(f"风险：{'、'.join(risks)}。")
        lines.append(f"估值判断：{valuation}。")
        lines.append(f"综合建议：{recommendation}。")
        return "".join(lines)
