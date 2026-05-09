"""Financial analyzer with LLM-powered analysis and rule-based fallback."""

import json
from typing import Optional

from tools.financial_reports.schemas import (
    AnalysisResult,
    DuPontAnalysis,
    FinancialMetrics,
    FiveDimensionScores,
)


class FinancialAnalyzer:
    """Analyzer that uses LLM for analysis with rule-based fallback."""

    def __init__(self, generator=None, persona_config=None):
        self.generator = generator
        self.persona_config = persona_config

    def analyze(
        self,
        stock_name: str,
        metrics_history: list[FinancialMetrics],
        raw_reports: list[str],
    ) -> AnalysisResult:
        """Analyze financial metrics and return an AnalysisResult.

        Tries LLM analysis first (if generator is available), then
        falls back to rule-based scoring.
        """
        if not metrics_history:
            return AnalysisResult(
                overall_health="未知",
                summary=f"未能提取{stock_name}的有效财务指标，无法进行分析。",
            )

        # Try LLM analysis first
        if self.generator is not None and getattr(self.generator, "llm_available", False):
            try:
                result = self._analyze_with_llm(stock_name, metrics_history, raw_reports)
                if result.overall_health:
                    return result
            except Exception:
                pass  # Fall through to rule-based fallback

        # Rule-based fallback
        du_pont = self._du_pont_analysis(metrics_history)
        scores = self._calculate_five_dim_scores(metrics_history)
        risks = self._identify_risks(metrics_history)
        strengths = self._identify_strengths(metrics_history)
        concerns = self._identify_concerns(metrics_history)
        overall = self._overall_health(scores)
        latest = metrics_history[-1]
        valuation = self._valuation_comment(latest, du_pont)
        recommendation = self._recommendation(overall, risks)
        summary = self._generate_summary(
            stock_name, overall, scores, du_pont, risks, strengths, concerns, valuation, recommendation
        )

        return AnalysisResult(
            overall_health=overall,
            risk_flags=risks,
            strengths=strengths,
            concerns=concerns,
            valuation_comment=valuation,
            recommendation=recommendation,
            summary=summary,
            du_pont=du_pont,
            five_dim_scores=scores,
        )

    # ------------------------------------------------------------------ #
    #  DuPont Analysis
    # ------------------------------------------------------------------ #

    def _du_pont_analysis(self, metrics_history: list[FinancialMetrics]) -> DuPontAnalysis:
        """Perform DuPont analysis: ROE = Net Margin × Asset Turnover × Equity Multiplier."""
        if not metrics_history:
            return DuPontAnalysis()

        latest = metrics_history[-1]
        net_margin = latest.net_margin
        asset_turnover = latest.asset_turnover
        debt_ratio = latest.debt_ratio
        roe = latest.roe

        # Estimate equity multiplier from debt_ratio if not directly available
        # Equity Multiplier = Total Assets / Total Equity = 1 / (1 - Debt Ratio)
        if debt_ratio is not None and debt_ratio < 100:
            equity_multiplier = 100.0 / (100.0 - debt_ratio)
        else:
            equity_multiplier = None

        # Calculate implied ROE from DuPont components
        if net_margin is not None and asset_turnover is not None and equity_multiplier is not None:
            implied_roe = net_margin * asset_turnover * equity_multiplier
        else:
            implied_roe = roe

        # Determine primary driver
        drivers = []
        if net_margin is not None:
            if net_margin >= 15:
                drivers.append("高净利率")
            elif net_margin >= 8:
                drivers.append("中等净利率")
            else:
                drivers.append("低净利率")

        if asset_turnover is not None:
            if asset_turnover >= 0.8:
                drivers.append("高资产周转")
            elif asset_turnover >= 0.4:
                drivers.append("中等资产周转")
            else:
                drivers.append("低资产周转")

        if equity_multiplier is not None:
            if equity_multiplier >= 3:
                drivers.append("高杠杆驱动")
            elif equity_multiplier >= 2:
                drivers.append("中等杠杆")
            else:
                drivers.append("低杠杆")

        driver_text = "，".join(drivers) if drivers else "数据不足，无法拆解"

        return DuPontAnalysis(
            net_margin=net_margin,
            asset_turnover=asset_turnover,
            equity_multiplier=equity_multiplier,
            roe=roe if roe is not None else implied_roe,
            driver=driver_text,
        )

    # ------------------------------------------------------------------ #
    #  Five-dimension scoring (Revenue / Profit / Cashflow / Balance / Shareholder)
    # ------------------------------------------------------------------ #

    def _calculate_five_dim_scores(
        self, metrics_history: list[FinancialMetrics]
    ) -> FiveDimensionScores:
        """Calculate five-dimension scores based on personality.md framework."""
        if not metrics_history:
            return FiveDimensionScores()

        latest = metrics_history[-1]
        prev = metrics_history[-2] if len(metrics_history) >= 2 else None

        # 1. 收入真实性 (Revenue Quality)
        revenue_quality = self._score_revenue_quality(latest, prev)

        # 2. 利润质量 (Profit Quality)
        profit_quality = self._score_profit_quality(latest, prev)

        # 3. 现金流健康 (Cashflow Health)
        cashflow_health = self._score_cashflow_health(latest)

        # 4. 资产负债表 (Balance Sheet)
        balance_score = self._score_balance_sheet(latest)

        # 5. 股东回报 (Shareholder Return)
        shareholder_score = self._score_shareholder_return(latest, prev)

        overall = (revenue_quality + profit_quality + cashflow_health + balance_score + shareholder_score) // 5

        return FiveDimensionScores(
            revenue_quality=revenue_quality,
            profit_quality=profit_quality,
            cashflow_health=cashflow_health,
            balance_sheet=balance_score,
            shareholder_return=shareholder_score,
            overall=overall,
        )

    def _score_revenue_quality(
        self, latest: FinancialMetrics, prev: Optional[FinancialMetrics]
    ) -> int:
        """Score revenue quality: 0-100."""
        score = 60  # baseline

        # Check accounts receivable vs revenue
        if latest.accounts_receivable is not None and latest.revenue is not None and latest.revenue > 0:
            ar_ratio = latest.accounts_receivable / latest.revenue
            if ar_ratio > 0.5:
                score -= 30  # High AR ratio
            elif ar_ratio > 0.3:
                score -= 15

        # Check revenue growth consistency
        if latest.revenue_yoy is not None:
            if latest.revenue_yoy < -10:
                score -= 20
            elif latest.revenue_yoy < 0:
                score -= 10
            elif latest.revenue_yoy >= 15:
                score += 15

        # Check if AR growing faster than revenue (warning sign)
        if prev is not None and latest.accounts_receivable is not None and prev.accounts_receivable is not None:
            if prev.accounts_receivable > 0:
                ar_growth = (latest.accounts_receivable - prev.accounts_receivable) / prev.accounts_receivable * 100
                if latest.revenue_yoy is not None and ar_growth > latest.revenue_yoy + 10:
                    score -= 25  # AR growing much faster than revenue

        return max(0, min(100, score))

    def _score_profit_quality(
        self, latest: FinancialMetrics, prev: Optional[FinancialMetrics]
    ) -> int:
        """Score profit quality: 0-100."""
        score = 60  # baseline

        # Check net profit excl nonrecurring vs net profit ratio
        if latest.net_profit_excl_nonrecurring is not None and latest.net_profit is not None and latest.net_profit > 0:
            nonrecurring_ratio = latest.net_profit_excl_nonrecurring / latest.net_profit
            if nonrecurring_ratio < 0.5:
                score -= 30  # Less than 50% is from core business
            elif nonrecurring_ratio < 0.7:
                score -= 15
            elif nonrecurring_ratio >= 0.9:
                score += 15

        # Check gross margin
        if latest.gross_margin is not None:
            if latest.gross_margin >= 40:
                score += 20
            elif latest.gross_margin >= 25:
                score += 10
            elif latest.gross_margin < 15:
                score -= 15

        # Check net margin
        if latest.net_margin is not None:
            if latest.net_margin >= 15:
                score += 15
            elif latest.net_margin < 3:
                score -= 15

        # Check margin stability
        if prev is not None and latest.gross_margin is not None and prev.gross_margin is not None:
            margin_change = abs(latest.gross_margin - prev.gross_margin)
            if margin_change > 10:
                score -= 15  # Large margin fluctuation

        return max(0, min(100, score))

    def _score_cashflow_health(self, latest: FinancialMetrics) -> int:
        """Score cashflow health: 0-100."""
        score = 60  # baseline

        # Operating cash flow / net profit ratio
        if latest.operating_cash_flow is not None and latest.net_profit is not None and latest.net_profit > 0:
            ocf_ratio = latest.operating_cash_flow / latest.net_profit
            if ocf_ratio >= 1.0:
                score += 25
            elif ocf_ratio >= 0.8:
                score += 15
            elif ocf_ratio >= 0.5:
                score += 0
            else:
                score -= 30  # Less than 50% of profit is real cash

        # Operating cash flow sign
        if latest.operating_cash_flow is not None:
            if latest.operating_cash_flow < 0:
                score -= 25  # Negative operating cash flow
            elif latest.operating_cash_flow > 0:
                score += 10

        # Free cash flow
        if latest.free_cash_flow is not None:
            if latest.free_cash_flow > 0:
                score += 15
            else:
                score -= 10

        return max(0, min(100, score))

    def _score_balance_sheet(self, latest: FinancialMetrics) -> int:
        """Score balance sheet health: 0-100."""
        score = 60  # baseline

        # Interest-bearing debt ratio
        if latest.interest_bearing_debt_ratio is not None:
            if latest.interest_bearing_debt_ratio <= 30:
                score += 20
            elif latest.interest_bearing_debt_ratio <= 50:
                score += 5
            else:
                score -= 25

        # Total debt ratio (fallback)
        elif latest.debt_ratio is not None:
            if latest.debt_ratio <= 40:
                score += 15
            elif latest.debt_ratio <= 60:
                score += 0
            else:
                score -= 20

        # Goodwill
        if latest.goodwill is not None:
            # We don't have total assets, so use a rough threshold
            if latest.goodwill > 50:  # 50亿以上商誉需警惕
                score -= 15

        # Current ratio
        if latest.current_ratio is not None:
            if latest.current_ratio >= 2:
                score += 15
            elif latest.current_ratio >= 1.5:
                score += 5
            elif latest.current_ratio < 1:
                score -= 20

        # Quick ratio
        if latest.quick_ratio is not None:
            if latest.quick_ratio >= 1:
                score += 10
            elif latest.quick_ratio < 0.8:
                score -= 10

        # Inventory turnover
        if latest.inventory_turnover_days is not None:
            if latest.inventory_turnover_days > 200:
                score -= 10  # Slow inventory turnover

        # Interest coverage
        if latest.interest_coverage is not None:
            if latest.interest_coverage >= 5:
                score += 10
            elif latest.interest_coverage < 2:
                score -= 15

        return max(0, min(100, score))

    def _score_shareholder_return(
        self, latest: FinancialMetrics, prev: Optional[FinancialMetrics]
    ) -> int:
        """Score shareholder return: 0-100."""
        score = 60  # baseline

        # ROE level
        if latest.roe is not None:
            if latest.roe >= 20:
                score += 25
            elif latest.roe >= 15:
                score += 15
            elif latest.roe >= 10:
                score += 5
            elif latest.roe < 5:
                score -= 20

        # ROE consistency
        if prev is not None and latest.roe is not None and prev.roe is not None:
            roe_change = abs(latest.roe - prev.roe)
            if roe_change > 10:
                score -= 15  # Large ROE fluctuation

        # Dividend rate
        if latest.dividend_rate is not None:
            if latest.dividend_rate >= 4:
                score += 15
            elif latest.dividend_rate >= 2:
                score += 5

        # Major shareholder pledge
        if latest.major_shareholder_pledge_ratio is not None:
            if latest.major_shareholder_pledge_ratio > 50:
                score -= 30  # High pledge ratio
            elif latest.major_shareholder_pledge_ratio > 30:
                score -= 15

        return max(0, min(100, score))

    # ------------------------------------------------------------------ #
    #  LLM analysis with persona prompt
    # ------------------------------------------------------------------ #

    def _analyze_with_llm(
        self,
        stock_name: str,
        metrics_history: list[FinancialMetrics],
        raw_reports: list[str],
    ) -> AnalysisResult:
        """Use LLM to analyze financial metrics and produce AnalysisResult."""
        system_prompt = self._build_analyzer_system_prompt()
        user_prompt = self._build_analysis_prompt(stock_name, metrics_history)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = self.generator._call_llm(messages)
        return self._parse_analysis_from_llm_response(response)

    def _build_analyzer_system_prompt(self) -> str:
        """Build system prompt infused with financial_analyst persona DNA."""
        lines = [
            "你是一位专业的财报分析师，基于《手把手教你读财报》的方法论，专注于通过财务数据识别企业真实经营状况。",
            "",
            "【核心能力】",
            "1. 财报排雷：识别财务造假信号、异常科目、隐藏风险",
            "2. 盈利能力分析：ROE、毛利率、净利率、费用率等核心指标",
            "3. 成长性评估：营收增长、利润增长、现金流增长",
            "4. 财务健康度：资产负债结构、偿债能力、营运效率",
            "5. 估值判断：结合财务数据给出估值区间建议",
            "",
            "【分析原则】",
            "1. 数据说话：所有判断必须基于财务数据，不凭感觉",
            "2. 历史对比：不仅看当期数据，更要看3-5年趋势",
            "3. 同业对比：与行业平均水平比较，识别异常",
            "4. 现金流优先：利润可以调节，现金流更真实",
            "5. 保守原则：宁可错过，不可踩雷",
            "",
            "【表达风格】",
            "- 专业严谨，但不失通俗",
            "- 用数据支撑观点，但不过度堆砌数字",
            "- 先讲结论，再讲依据",
            "- 风险提示要醒目",
            "",
            "【五维排雷清单 - 必须逐条检查】",
            "",
            "### 1. 收入真实性",
            "- 营收增长是否与现金流匹配：如果营收增长但经营现金流下降或大幅低于净利润，存在收入虚增风险",
            "- 应收账款是否异常增长：应收账款增速持续高于营收增速，可能通过赊销虚增收入",
            "- 关联交易占比是否过高：关联交易占营收比例过高，存在利益输送或收入调节风险",
            "",
            "### 2. 利润质量",
            "- 扣非净利润 vs 净利润：扣非净利润与净利润差距过大，说明主营业务盈利能力弱，依赖非经常性损益",
            "- 非经常性损益占比：非经常性损益占净利润比例过高（如超过20%），利润质量差",
            "- 毛利率是否异常波动：毛利率突然大幅上升或下降，需警惕会计调节或行业竞争恶化",
            "",
            "### 3. 现金流健康",
            "- 经营现金流是否为正：经营现金流持续为负，企业处于'失血'状态",
            "- 经营现金流/净利润比值：理想值应大于1。如果长期低于0.5，说明利润含金量低",
            "- 自由现金流情况：经营现金流减去资本支出后的自由现金流，反映企业真实的造血能力",
            "",
            "### 4. 资产负债表",
            "- 有息负债率：有息负债占总资产比例过高（超过50%），财务风险大",
            "- 商誉占比：商誉占总资产比例过高（超过20%），存在减值爆雷风险",
            "- 存货周转天数：存货周转天数持续增加，可能产品滞销或存在存货减值风险",
            "- 流动比率和速动比率：流动比率低于1.5或速动比率低于0.8，短期偿债压力大",
            "",
            "### 5. 股东回报",
            "- ROE持续性：ROE是否持续稳定在15%以上，还是大起大落。持续性比峰值更重要",
            "- 分红率：分红率是否稳定，是否存在'铁公鸡'或突然大幅提高分红掩护大股东减持",
            "- 股权结构：股权是否过于集中或分散，是否存在大股东质押比例过高等治理风险",
            "",
            "【杜邦分析框架】",
            "ROE = 净利率 × 资产周转率 × 权益乘数",
            "- 高净利率型（如茅台）：品牌护城河，最健康",
            "- 高周转率型（如零售）：薄利多销，管理要求高",
            "- 高杠杆型（如银行）：用别人的钱赚钱，风险也高",
            "分析时必须拆解ROE的驱动因素，判断高ROE是否可持续",
            "",
            "【输出格式要求】",
            "每次分析必须包含以下字段，以严格JSON格式返回：",
            '- overall_health: 综合健康度评级（优秀/良好/一般/差）',
            '- risk_flags: 关键风险点列表（红色警报，不能为空数组）',
            '- strengths: 核心优势列表（绿色信号）',
            '- concerns: 关注点列表（需要跟踪但暂不构成风险的事项）',
            '- valuation_comment: 估值判断（一段话，给出估值区间和逻辑）',
            '- recommendation: 明确建议（买入/持有/观望/回避）',
            '- summary: 综合总结（包含评级、关键指标、优势、风险、建议的完整段落）',
            '- du_pont: 杜邦分析对象 {driver: "驱动因素描述", roe: 数值}',
            '- five_dim_scores: 五维评分对象 {revenue_quality, profit_quality, cashflow_health, balance_sheet, shareholder_return, overall}',
            "",
            "【重要约束】",
            "- 只返回 JSON，不要任何解释或 markdown 代码块",
            "- recommendation 必须是：买入、持有、观望、回避 之一",
            "- overall_health 必须是：优秀、良好、一般、差 之一",
            "- risk_flags 不能为空，至少要有1-2条风险或'暂无重大风险'",
            "- 所有判断必须有数据支撑，禁止凭空猜测",
        ]

        # Inject persona identity and values if available
        if self.persona_config is not None:
            identity = getattr(self.persona_config, "identity", "")
            if identity:
                lines.insert(0, f"【身份】{identity}")
                lines.insert(1, "")

            values = getattr(self.persona_config, "values", {})
            if values.get("pursue"):
                lines.append("")
                lines.append("【价值观驱动】")
                for pursuit in values["pursue"][:5]:
                    lines.append(f"- 追求：{pursuit}")
            if values.get("reject"):
                lines.append("")
                lines.append("【必须拒绝】")
                for reject in values["reject"][:5]:
                    lines.append(f"- {reject}")

        return "\n".join(lines)

    def _build_analysis_prompt(
        self,
        stock_name: str,
        metrics_history: list[FinancialMetrics],
    ) -> str:
        """Build the analysis prompt for LLM."""
        # Build metrics summary from newest to oldest
        metrics_lines = []
        for i, m in enumerate(reversed(metrics_history)):
            period_label = f"第{i+1}期（最新）" if i == 0 else f"第{i+1}期"
            fields = []
            if m.revenue is not None:
                fields.append(f"营收: {m.revenue:.2f}亿")
            if m.revenue_yoy is not None:
                fields.append(f"营收同比: {m.revenue_yoy:.2f}%")
            if m.net_profit is not None:
                fields.append(f"净利润: {m.net_profit:.2f}亿")
            if m.net_profit_yoy is not None:
                fields.append(f"净利同比: {m.net_profit_yoy:.2f}%")
            if m.net_profit_excl_nonrecurring is not None:
                fields.append(f"扣非净利润: {m.net_profit_excl_nonrecurring:.2f}亿")
            if m.non_recurring_income is not None:
                fields.append(f"非经常性损益: {m.non_recurring_income:.2f}亿")
            if m.roe is not None:
                fields.append(f"ROE: {m.roe:.1f}%")
            if m.gross_margin is not None:
                fields.append(f"毛利率: {m.gross_margin:.1f}%")
            if m.net_margin is not None:
                fields.append(f"净利率: {m.net_margin:.1f}%")
            if m.expense_ratio is not None:
                fields.append(f"费用率: {m.expense_ratio:.1f}%")
            if m.accounts_receivable is not None:
                fields.append(f"应收账款: {m.accounts_receivable:.2f}亿")
            if m.asset_turnover is not None:
                fields.append(f"资产周转率: {m.asset_turnover:.2f}")
            if m.operating_cash_flow is not None:
                fields.append(f"经营现金流: {m.operating_cash_flow:.2f}亿")
            if m.free_cash_flow is not None:
                fields.append(f"自由现金流: {m.free_cash_flow:.2f}亿")
            if m.debt_ratio is not None:
                fields.append(f"资产负债率: {m.debt_ratio:.1f}%")
            if m.interest_bearing_debt_ratio is not None:
                fields.append(f"有息负债率: {m.interest_bearing_debt_ratio:.1f}%")
            if m.goodwill is not None:
                fields.append(f"商誉: {m.goodwill:.2f}亿")
            if m.current_ratio is not None:
                fields.append(f"流动比率: {m.current_ratio:.2f}")
            if m.quick_ratio is not None:
                fields.append(f"速动比率: {m.quick_ratio:.2f}")
            if m.interest_coverage is not None:
                fields.append(f"利息保障倍数: {m.interest_coverage:.1f}")
            if m.dividend_rate is not None:
                fields.append(f"分红率: {m.dividend_rate:.1f}%")
            if m.major_shareholder_pledge_ratio is not None:
                fields.append(f"大股东质押: {m.major_shareholder_pledge_ratio:.1f}%")
            if m.eps is not None:
                fields.append(f"EPS: {m.eps:.2f}元")
            metrics_lines.append(f"{period_label}: {', '.join(fields)}")

        metrics_text = "\n".join(metrics_lines)

        prompt = (
            f"请对 {stock_name} 进行财务健康度分析。\n\n"
            f"财务指标历史（从新到旧）：\n{metrics_text}\n\n"
            "分析要求（请严格遵循五维排雷清单和杜邦分析框架）：\n"
            "1. 综合评估财务健康度（优秀/良好/一般/差），必须基于数据\n"
            "2. 进行杜邦分析：拆解ROE = 净利率 × 资产周转率 × 权益乘数，判断高ROE是否可持续\n"
            "3. 五维排雷逐条检查：收入真实性、利润质量、现金流健康、资产负债表、股东回报\n"
            "4. 识别风险点（列表）。重点关注：经营现金流与净利润是否匹配、应收账款是否异常、负债率是否过高\n"
            "5. 识别核心优势（列表）。如ROE持续性、毛利率稳定性、现金流充沛度\n"
            "6. 识别关注点（列表）。需要持续跟踪但暂不构成风险的事项\n"
            "7. 给出估值判断。基于盈利能力（ROE）、护城河（毛利率）、成长性综合判断\n"
            "8. 给出投资建议（买入/持有/观望/回避）。遵循保守原则：宁可错过，不可踩雷\n"
            "9. 生成一段综合总结。先讲结论，再讲依据，风险提示要醒目\n\n"
            "返回严格 JSON 格式：\n"
            "{\n"
            '  "overall_health": "优秀/良好/一般/差",\n'
            '  "risk_flags": ["...", "..."],\n'
            '  "strengths": ["...", "..."],\n'
            '  "concerns": ["...", "..."],\n'
            '  "valuation_comment": "...",\n'
            '  "recommendation": "买入/持有/观望/回避",\n'
            '  "summary": "...",\n'
            '  "du_pont": {"driver": "高净利率+低杠杆", "roe": 18.5},\n'
            '  "five_dim_scores": {"revenue_quality": 75, "profit_quality": 80, "cashflow_health": 60, "balance_sheet": 70, "shareholder_return": 85, "overall": 74}\n'
            "}"
        )
        return prompt

    def _parse_analysis_from_llm_response(self, response: str) -> AnalysisResult:
        """Parse JSON response from LLM into AnalysisResult."""
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)

        rec = data.get("recommendation", "")
        valid_recs = ("买入", "持有", "观望", "回避", "")
        if rec not in valid_recs:
            rec = ""

        # Parse du_pont
        du_pont_data = data.get("du_pont", {})
        du_pont = DuPontAnalysis(
            driver=du_pont_data.get("driver", ""),
            roe=du_pont_data.get("roe"),
        )

        # Parse five_dim_scores
        scores_data = data.get("five_dim_scores", {})
        scores = FiveDimensionScores(
            revenue_quality=scores_data.get("revenue_quality", 0),
            profit_quality=scores_data.get("profit_quality", 0),
            cashflow_health=scores_data.get("cashflow_health", 0),
            balance_sheet=scores_data.get("balance_sheet", 0),
            shareholder_return=scores_data.get("shareholder_return", 0),
            overall=scores_data.get("overall", 0),
        )

        return AnalysisResult(
            overall_health=data.get("overall_health", ""),
            risk_flags=data.get("risk_flags") or [],
            strengths=data.get("strengths") or [],
            concerns=data.get("concerns") or [],
            valuation_comment=data.get("valuation_comment", ""),
            recommendation=rec,
            summary=data.get("summary", ""),
            du_pont=du_pont,
            five_dim_scores=scores,
        )

    # ------------------------------------------------------------------ #
    #  Rule-based fallback methods
    # ------------------------------------------------------------------ #

    def _overall_health(self, scores: FiveDimensionScores) -> str:
        """Map aggregate scores to overall health rating."""
        avg = scores.overall
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

        # Debt risks
        if latest.interest_bearing_debt_ratio is not None and latest.interest_bearing_debt_ratio > 50:
            risks.append("有息负债率过高")
        elif latest.debt_ratio is not None and latest.debt_ratio > 70:
            risks.append("资产负债率过高")

        # Cashflow risks
        if latest.operating_cash_flow is not None and latest.net_profit is not None:
            if latest.net_profit > 0 and latest.operating_cash_flow < latest.net_profit * 0.5:
                risks.append("经营现金流大幅低于净利润")
        if latest.operating_cash_flow is not None and latest.operating_cash_flow < 0:
            risks.append("经营现金流为负")

        # Revenue decline
        if len(metrics_history) >= 2:
            prev = metrics_history[-2]
            if prev.revenue is not None and latest.revenue is not None and prev.revenue > 0:
                if latest.revenue < prev.revenue * 0.9:
                    risks.append("营收同比下滑明显")
            if prev.net_profit is not None and latest.net_profit is not None and prev.net_profit > 0:
                if latest.net_profit < prev.net_profit * 0.9:
                    risks.append("净利润同比下滑明显")

        # AR risk
        if latest.accounts_receivable is not None and latest.revenue is not None and latest.revenue > 0:
            ar_ratio = latest.accounts_receivable / latest.revenue
            if ar_ratio > 0.5:
                risks.append(f"应收账款占营收比例过高({ar_ratio:.0%})")

        # Profit quality risk
        if latest.net_profit_excl_nonrecurring is not None and latest.net_profit is not None and latest.net_profit > 0:
            ratio = latest.net_profit_excl_nonrecurring / latest.net_profit
            if ratio < 0.5:
                risks.append("扣非净利润占比过低，利润质量差")

        # Goodwill risk
        if latest.goodwill is not None and latest.goodwill > 50:
            risks.append(f"商誉规模较大({latest.goodwill:.0f}亿)，存在减值风险")

        # Pledge risk
        if latest.major_shareholder_pledge_ratio is not None and latest.major_shareholder_pledge_ratio > 50:
            risks.append("大股东质押比例过高")

        # Liquidity risk
        if latest.current_ratio is not None and latest.current_ratio < 1:
            risks.append("流动比率低于1，短期偿债压力大")

        if not risks:
            risks.append("暂无重大风险")

        return risks

    def _identify_strengths(self, metrics_history: list[FinancialMetrics]) -> list[str]:
        """Identify financial strengths."""
        strengths: list[str] = []
        if not metrics_history:
            return strengths
        latest = metrics_history[-1]

        if latest.roe is not None and latest.roe >= 15:
            strengths.append(f"净资产收益率优秀({latest.roe:.1f}%)")
        if latest.gross_margin is not None and latest.gross_margin >= 30:
            strengths.append(f"毛利率水平较高({latest.gross_margin:.1f}%)")
        if latest.operating_cash_flow is not None and latest.net_profit is not None:
            if latest.net_profit > 0 and latest.operating_cash_flow >= latest.net_profit * 0.8:
                strengths.append("经营现金流健康")
        if latest.debt_ratio is not None and latest.debt_ratio <= 40:
            strengths.append("负债率较低，财务结构稳健")
        if latest.free_cash_flow is not None and latest.free_cash_flow > 0:
            strengths.append("自由现金流为正，造血能力良好")
        if latest.current_ratio is not None and latest.current_ratio >= 2:
            strengths.append("流动比率充足，短期偿债无忧")
        if latest.dividend_rate is not None and latest.dividend_rate >= 3:
            strengths.append(f"分红率可观({latest.dividend_rate:.1f}%)")

        return strengths

    def _identify_concerns(self, metrics_history: list[FinancialMetrics]) -> list[str]:
        """Identify areas of concern."""
        concerns: list[str] = []
        if not metrics_history:
            return concerns
        latest = metrics_history[-1]

        if latest.roe is not None and latest.roe < 10:
            concerns.append(f"净资产收益率偏低({latest.roe:.1f}%)")
        if latest.gross_margin is not None and latest.gross_margin < 20:
            concerns.append(f"毛利率水平偏低({latest.gross_margin:.1f}%)")
        if latest.net_margin is not None and latest.net_margin < 5:
            concerns.append(f"净利率偏低({latest.net_margin:.1f}%)")
        if latest.debt_ratio is not None and 50 < latest.debt_ratio <= 70:
            concerns.append(f"负债率处于较高水平({latest.debt_ratio:.1f}%)")
        if latest.inventory_turnover_days is not None and latest.inventory_turnover_days > 150:
            concerns.append(f"存货周转天数较长({latest.inventory_turnover_days:.0f}天)")
        if latest.major_shareholder_pledge_ratio is not None and 30 < latest.major_shareholder_pledge_ratio <= 50:
            concerns.append(f"大股东质押比例需关注({latest.major_shareholder_pledge_ratio:.1f}%)")

        return concerns

    def _valuation_comment(self, latest: FinancialMetrics, du_pont: DuPontAnalysis) -> str:
        """Generate a valuation comment based on latest metrics."""
        parts: list[str] = []
        if latest.roe is not None and latest.roe >= 20:
            parts.append("盈利能力强劲")
        if latest.gross_margin is not None and latest.gross_margin >= 50:
            parts.append("高毛利护城河")
        if latest.net_margin is not None and latest.net_margin >= 20:
            parts.append("净利率优秀")
        if du_pont.driver:
            parts.append(f"杜邦拆解：{du_pont.driver}")

        if not parts:
            return "缺乏完整估值数据，无法给出估值判断"

        comment = "，".join(parts)
        if latest.roe is not None:
            if latest.roe >= 20:
                comment += "。属于高盈利质量标的，可给予合理溢价估值。"
            elif latest.roe >= 15:
                comment += "。盈利能力良好，按行业平均 PE 估值。"
            else:
                comment += "。盈利能力一般，需折价估值。"
        return comment

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
        scores: FiveDimensionScores,
        du_pont: DuPontAnalysis,
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
            f"五维评分——收入真实性:{scores.revenue_quality} 利润质量:{scores.profit_quality} "
            f"现金流:{scores.cashflow_health} 资产负债表:{scores.balance_sheet} "
            f"股东回报:{scores.shareholder_return}（综合{scores.overall}分）。"
        )
        if du_pont.driver:
            lines.append(f"杜邦分析：ROE驱动因素为{du_pont.driver}。")
        if strengths:
            lines.append(f"优势：{'、'.join(strengths)}。")
        if concerns:
            lines.append(f"关注点：{'、'.join(concerns)}。")
        if risks and risks != ["暂无重大风险"]:
            lines.append(f"风险：{'、'.join(risks)}。")
        lines.append(f"估值判断：{valuation}")
        lines.append(f"综合建议：{recommendation}。")
        return "".join(lines)
