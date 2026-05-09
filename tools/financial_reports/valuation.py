"""Valuation analyzer: PE / PB / PS methods with judgment logic."""

from dataclasses import dataclass
from typing import Optional

from tools.financial_reports.schemas import FinancialMetrics


@dataclass
class ValuationResult:
    """Result of multi-method valuation analysis."""
    pe: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None
    pe_judgment: str = ""       # 低估/合理/高估/无法判断
    pb_judgment: str = ""       # 低估/合理/高估/无法判断
    ps_judgment: str = ""       # 低估/合理/高估/无法判断
    overall_judgment: str = ""  # 综合估值判断
    fair_price_range: str = ""  # 合理价格区间描述


class ValuationAnalyzer:
    """Valuation analyzer implementing PE / PB / PS methods.

    Based on financial_analyst personality.md valuation framework:
    - PE: for stable profit companies (consumer, pharma)
    - PB: for asset-heavy or cyclical companies (banks, real estate, manufacturing)
    - PS: for high-growth but not-yet-profitable companies (some tech)
    """

    def __init__(self):
        pass

    def analyze(
        self,
        metrics: FinancialMetrics,
        stock_price: Optional[float] = None,
        total_shares: Optional[float] = None,  # 亿股
        net_assets: Optional[float] = None,     # 净资产，亿元
        industry_avg_pe: Optional[float] = None,
        industry_avg_pb: Optional[float] = None,
    ) -> ValuationResult:
        """Run valuation analysis using available methods.

        Args:
            metrics: Latest financial metrics
            stock_price: Current stock price (元)
            total_shares: Total shares outstanding (亿股)
            net_assets: Net assets / equity (亿元)
            industry_avg_pe: Industry average PE ratio
            industry_avg_pb: Industry average PB ratio

        Returns:
            ValuationResult with judgments for each method
        """
        result = ValuationResult()

        # Calculate PE
        if stock_price is not None and metrics.eps is not None and metrics.eps > 0:
            result.pe = stock_price / metrics.eps
            result.pe_judgment = self._judge_pe(
                result.pe, metrics.net_profit_yoy, industry_avg_pe
            )

        # Calculate PB
        if stock_price is not None and total_shares is not None and net_assets is not None:
            if total_shares > 0 and net_assets > 0:
                pbv = net_assets / total_shares  # 每股净资产
                if pbv > 0:
                    result.pb = stock_price / pbv
                    result.pb_judgment = self._judge_pb(
                        result.pb, metrics.roe, industry_avg_pb
                    )

        # Calculate PS
        if (
            stock_price is not None
            and total_shares is not None
            and metrics.revenue is not None
            and total_shares > 0
            and metrics.revenue > 0
        ):
            # PS = 总市值 / 营收 = (股价 × 总股本) / 营收
            market_cap = stock_price * total_shares  # 亿元
            result.ps = market_cap / metrics.revenue
            result.ps_judgment = self._judge_ps(result.ps, metrics.revenue_yoy)

        # Overall judgment
        result.overall_judgment = self._overall_valuation_judgment(result)
        result.fair_price_range = self._fair_price_range(
            metrics, result, stock_price, total_shares
        )

        return result

    def _judge_pe(
        self, pe: float, profit_growth: Optional[float], industry_avg: Optional[float]
    ) -> str:
        """Judge if PE is undervalued / fair / overvalued.

        Logic:
        - PEG < 1 → 低估（成长匹配估值）
        - PE < 行业平均 × 0.7 → 低估
        - PE > 行业平均 × 1.5 → 高估
        - 其他 → 合理
        """
        # PEG-based judgment (priority)
        if profit_growth is not None and profit_growth > 0:
            peg = pe / profit_growth
            if peg < 1:
                return "低估"
            elif peg > 2:
                return "高估"

        # Industry comparison
        if industry_avg is not None and industry_avg > 0:
            if pe < industry_avg * 0.7:
                return "低估"
            elif pe > industry_avg * 1.5:
                return "高估"
            else:
                return "合理"

        # Absolute thresholds (fallback)
        if pe < 15:
            return "低估"
        elif pe > 40:
            return "高估"
        else:
            return "合理"

    def _judge_pb(self, pb: float, roe: Optional[float], industry_avg: Optional[float]) -> str:
        """Judge if PB is undervalued / fair / overvalued.

        Logic:
        - ROE >= 15% + PB < 3 → 合理或低估
        - ROE < 10% + PB > 2 → 高估
        - PB < 1 → 破净（可能是价值陷阱）
        """
        if industry_avg is not None and industry_avg > 0:
            if pb < industry_avg * 0.7:
                return "低估"
            elif pb > industry_avg * 1.5:
                return "高估"

        if pb < 1:
            # 破净需结合 ROE 判断
            if roe is not None and roe >= 10:
                return "低估（破净但ROE尚可）"
            else:
                return "破净（警惕价值陷阱）"

        if roe is not None:
            if roe >= 15 and pb <= 3:
                return "合理"
            elif roe >= 15 and pb > 5:
                return "高估"
            elif roe < 10 and pb > 2:
                return "高估"

        if pb < 1.5:
            return "低估"
        elif pb > 4:
            return "高估"
        else:
            return "合理"

    def _judge_ps(self, ps: float, revenue_growth: Optional[float]) -> str:
        """Judge if PS is undervalued / fair / overvalued.

        PS is mainly for growth companies. Higher growth justifies higher PS.
        """
        if revenue_growth is not None and revenue_growth > 0:
            # Rough rule: PS / growth_rate < 0.5 → 低估, > 1.5 → 高估
            ratio = ps / revenue_growth
            if ratio < 0.5:
                return "低估"
            elif ratio > 1.5:
                return "高估"
            else:
                return "合理"

        if ps < 3:
            return "低估"
        elif ps > 10:
            return "高估"
        else:
            return "合理"

    def _overall_valuation_judgment(self, result: ValuationResult) -> str:
        """Combine all methods into an overall valuation judgment."""
        judgments = [j for j in [result.pe_judgment, result.pb_judgment, result.ps_judgment] if j]

        if not judgments:
            return "数据不足，无法估值"

        # Count categories
        low = sum(1 for j in judgments if "低估" in j)
        high = sum(1 for j in judgments if "高估" in j)
        fair = sum(1 for j in judgments if "合理" in j)
        trap = sum(1 for j in judgments if "陷阱" in j)

        if trap >= 1:
            return "警惕价值陷阱"
        if low >= 2:
            return "整体低估"
        if high >= 2:
            return "整体高估"
        if low >= 1 and fair >= 1:
            return "偏低或合理"
        if high >= 1 and fair >= 1:
            return "偏高或合理"
        if fair >= 2:
            return "估值合理"

        return "估值判断存在分歧"

    def _fair_price_range(
        self,
        metrics: FinancialMetrics,
        result: ValuationResult,
        stock_price: Optional[float],
        total_shares: Optional[float],
    ) -> str:
        """Estimate fair price range based on PE and PB methods."""
        ranges: list[str] = []

        # PE-based fair price
        if result.pe is not None and metrics.eps is not None and metrics.eps > 0:
            if metrics.net_profit_yoy is not None and metrics.net_profit_yoy > 0:
                # Use growth-adjusted PE
                fair_pe = min(metrics.net_profit_yoy * 1.2, 30)  # Cap at 30x
            else:
                fair_pe = 15  # Default for no-growth
            fair_price_pe = metrics.eps * fair_pe
            ranges.append(f"PE法: 约{fair_price_pe:.1f}元（按{fair_pe:.0f}倍PE）")

        # PB-based fair price
        if (
            result.pb is not None
            and stock_price is not None
            and total_shares is not None
            and total_shares > 0
        ):
            # Rough estimate: fair PB depends on ROE
            if metrics.roe is not None:
                fair_pb = metrics.roe / 10  # Rough rule: ROE 15% → PB 1.5
                fair_pb = max(0.8, min(fair_pb, 5))
            else:
                fair_pb = 1.5
            current_bvps = stock_price / result.pb  # 每股净资产
            fair_price_pb = current_bvps * fair_pb
            ranges.append(f"PB法: 约{fair_price_pb:.1f}元（按{fair_pb:.1f}倍PB）")

        if not ranges:
            return "缺乏数据，无法估算合理价格"

        return "；".join(ranges)

    def to_valuation_comment(self, result: ValuationResult) -> str:
        """Convert ValuationResult to a human-readable comment."""
        parts: list[str] = []

        if result.pe is not None:
            parts.append(f"PE: {result.pe:.1f}倍（{result.pe_judgment}）")
        if result.pb is not None:
            parts.append(f"PB: {result.pb:.1f}倍（{result.pb_judgment}）")
        if result.ps is not None:
            parts.append(f"PS: {result.ps:.1f}倍（{result.ps_judgment}）")

        if not parts:
            return "缺乏估值数据，无法给出估值判断"

        comment = "；".join(parts)
        comment += f"。综合判断：{result.overall_judgment}。"
        if result.fair_price_range:
            comment += f"合理价格参考：{result.fair_price_range}。"
        return comment
