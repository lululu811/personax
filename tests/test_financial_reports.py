def test_financial_report_dataclass():
    from tools.financial_reports.schemas import FinancialReport
    report = FinancialReport(
        stock_code="600519",
        stock_name="贵州茅台",
        report_type="annual",
        year=2024,
        period="2024年度",
        pdf_path="/tmp/test.pdf",
        raw_text="营业收入: 100亿",
    )
    assert report.stock_code == "600519"
    assert report.report_type == "annual"

def test_financial_metrics_dataclass():
    from tools.financial_reports.schemas import FinancialMetrics
    metrics = FinancialMetrics(
        revenue=100.0,
        revenue_yoy=15.5,
        net_profit=50.0,
        net_profit_yoy=20.0,
        roe=25.0,
        gross_margin=90.0,
        net_margin=50.0,
        debt_ratio=30.0,
        operating_cash_flow=60.0,
        eps=40.0,
    )
    assert metrics.revenue == 100.0
    assert metrics.roe == 25.0

def test_analysis_result_dataclass():
    from tools.financial_reports.schemas import AnalysisResult
    result = AnalysisResult(
        overall_health="优秀",
        risk_flags=["应收账款增长较快"],
        strengths=["毛利率稳定", "现金流充沛"],
        concerns=["库存增加"],
        valuation_comment="估值合理，处于历史中位数",
        recommendation="持有",
        summary="整体财务健康，建议继续持有",
    )
    assert result.overall_health == "优秀"
    assert result.recommendation == "持有"


def test_financial_report_defaults():
    from tools.financial_reports.schemas import FinancialReport
    report = FinancialReport(
        stock_code="000001",
        stock_name="平安银行",
        report_type="q1",
        year=2024,
        period="2024Q1",
        pdf_path="/tmp/test.pdf",
    )
    assert report.raw_text == ""


def test_financial_metrics_defaults():
    from tools.financial_reports.schemas import FinancialMetrics
    metrics = FinancialMetrics()
    assert metrics.revenue is None
    assert metrics.roe is None
    assert metrics.debt_ratio is None


def test_financial_metrics_partial():
    from tools.financial_reports.schemas import FinancialMetrics
    metrics = FinancialMetrics(revenue=100.0, roe=15.0)
    assert metrics.revenue == 100.0
    assert metrics.roe == 15.0
    assert metrics.net_profit is None


def test_analysis_result_defaults():
    from tools.financial_reports.schemas import AnalysisResult
    result = AnalysisResult()
    assert result.overall_health == ""
    assert result.risk_flags == []
    assert result.strengths == []
    assert result.concerns == []


def test_analysis_result_edge_cases():
    from tools.financial_reports.schemas import AnalysisResult
    result = AnalysisResult(
        overall_health="差",
        risk_flags=["商誉过高", "现金流紧张", "负债率飙升"],
        strengths=[],
        concerns=["大股东减持", "审计非标"],
        valuation_comment="严重高估",
        recommendation="回避",
        summary="多项指标恶化，建议回避",
    )
    assert len(result.risk_flags) == 3
    assert result.strengths == []
    assert result.recommendation == "回避"


def test_default_list_isolation():
    from tools.financial_reports.schemas import AnalysisResult
    a = AnalysisResult()
    b = AnalysisResult()
    a.risk_flags.append("test")
    assert b.risk_flags == []
    assert a.risk_flags == ["test"]


class TestDownloader:
    def test_find_stock_by_code(self):
        from tools.financial_reports.downloader import CnInfoDownloader
        downloader = CnInfoDownloader()
        code, info, market = downloader.find_stock("600519")
        assert code == "600519"
        assert market == "szse"
        assert info is not None

    def test_detect_market_a_share(self):
        from tools.financial_reports.downloader import CnInfoDownloader
        d = CnInfoDownloader()
        assert d._detect_market("600519") == "szse"
        assert d._detect_market("000001") == "szse"
        assert d._detect_market("300001") == "szse"

    def test_detect_market_hk(self):
        from tools.financial_reports.downloader import CnInfoDownloader
        d = CnInfoDownloader()
        assert d._detect_market("00700") == "hke"
        assert d._detect_market("09988") == "hke"

    def test_to_chinese_year(self):
        from tools.financial_reports.downloader import to_chinese_year
        assert to_chinese_year(2024) == "二零二四"
        assert to_chinese_year(1999) == "一九九九"


class TestExtractor:
    def test_extract_nonexistent_file(self, tmp_path):
        from tools.financial_reports.extractor import PDFExtractor
        extractor = PDFExtractor()
        text, metrics = extractor.extract(str(tmp_path / "nonexistent.pdf"))
        assert text == ""
        assert metrics.revenue is None

    def test_clean_financial_text(self):
        from tools.financial_reports.extractor import PDFExtractor
        extractor = PDFExtractor()
        raw = "  营业收入  \n\n\n  100亿元  "
        cleaned = extractor._clean_text(raw)
        assert "营业收入" in cleaned
        assert "  " not in cleaned

    def test_extract_metrics_from_text_regex(self):
        from tools.financial_reports.extractor import PDFExtractor
        from tools.financial_reports.schemas import FinancialMetrics
        extractor = PDFExtractor()
        text = (
            "营业收入: 150.5\n"
            "净利润: 50.2\n"
            "加权平均净资产收益率: 18.5\n"
            "毛利率: 35.0\n"
            "净利率: 15.0\n"
            "资产负债率: 45.0\n"
            "经营活动产生的现金流量净额: 30.0\n"
            "基本每股收益: 2.5\n"
        )
        metrics = extractor._extract_metrics_from_text(text)
        assert metrics.revenue == 150.5
        assert metrics.net_profit == 50.2
        assert metrics.roe == 18.5
        assert metrics.gross_margin == 35.0
        assert metrics.net_margin == 15.0
        assert metrics.debt_ratio == 45.0
        assert metrics.operating_cash_flow == 30.0
        assert metrics.eps == 2.5

    def test_extract_metrics_llm_path(self):
        from tools.financial_reports.extractor import PDFExtractor
        from tools.financial_reports.schemas import FinancialMetrics

        class FakeGenerator:
            llm_available = True
            def _call_llm(self, messages):
                return (
                    '{"revenue": 200.0, "revenue_yoy": 10.5, "net_profit": 80.0, '
                    '"net_profit_yoy": 15.0, "roe": 22.0, "gross_margin": 40.0, '
                    '"net_margin": 20.0, "debt_ratio": 35.0, '
                    '"operating_cash_flow": 60.0, "eps": 3.0}'
                )

        extractor = PDFExtractor(generator=FakeGenerator())
        text = "任意财报文本"
        metrics = extractor._extract_metrics_with_llm(text)
        assert metrics.revenue == 200.0
        assert metrics.net_profit == 80.0
        assert metrics.roe == 22.0
        assert metrics.eps == 3.0

    def test_extract_llm_fallback_to_regex(self, tmp_path):
        from tools.financial_reports.extractor import PDFExtractor

        class FakeGenerator:
            llm_available = True
            def _call_llm(self, messages):
                raise RuntimeError("LLM 失败")

        extractor = PDFExtractor(generator=FakeGenerator())
        # Create a real file so os.path.exists passes, then mock _extract_text
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_text("dummy", encoding="utf-8")
        extractor._extract_text = lambda path: "营业收入: 999.0\n净利润: 111.0\n"
        raw_text, metrics = extractor.extract(str(fake_pdf))
        assert metrics.revenue == 999.0
        assert metrics.net_profit == 111.0

    def test_extract_llm_empty_fallback(self, tmp_path):
        from tools.financial_reports.extractor import PDFExtractor

        class FakeGenerator:
            llm_available = True
            def _call_llm(self, messages):
                return '{"revenue": null, "net_profit": null}'

        extractor = PDFExtractor(generator=FakeGenerator())
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_text("dummy", encoding="utf-8")
        extractor._extract_text = lambda path: "营业收入: 888.0\n"
        # LLM returns nulls, should fallback to regex
        raw_text, metrics = extractor.extract(str(fake_pdf))
        assert metrics.revenue == 888.0


class TestAnalyzer:
    def test_analyze_with_mock_metrics(self):
        from tools.financial_reports.analyzer import FinancialAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics

        analyzer = FinancialAnalyzer()
        metrics_history = [
            FinancialMetrics(revenue=100, net_profit=50, roe=25, gross_margin=90),
            FinancialMetrics(revenue=120, net_profit=60, roe=26, gross_margin=91),
        ]
        result = analyzer.analyze("贵州茅台", metrics_history, ["raw text"])

        assert result.overall_health in ["优秀", "良好", "一般", "差"]
        assert result.recommendation in ["买入", "持有", "观望", "回避"]
        assert result.summary != ""

    def test_analyze_empty_metrics(self):
        from tools.financial_reports.analyzer import FinancialAnalyzer
        analyzer = FinancialAnalyzer()
        result = analyzer.analyze("Test", [], [])
        assert result.overall_health == "未知"
        assert "未能提取" in result.summary

    def test_analyze_llm_path(self):
        from tools.financial_reports.analyzer import FinancialAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics

        class FakeGenerator:
            llm_available = True
            def _call_llm(self, messages):
                return (
                    '{"overall_health": "优秀", "risk_flags": [], '
                    '"strengths": ["ROE高"], "concerns": [], '
                    '"valuation_comment": "估值合理", '
                    '"recommendation": "买入", '
                    '"summary": "基本面优秀，建议买入"}'
                )

        analyzer = FinancialAnalyzer(generator=FakeGenerator())
        metrics = [FinancialMetrics(revenue=100, roe=25)]
        result = analyzer.analyze("Test", metrics, ["raw"])
        assert result.overall_health == "优秀"
        assert result.recommendation == "买入"
        assert result.strengths == ["ROE高"]
        assert result.summary == "基本面优秀，建议买入"

    def test_analyze_llm_fallback_to_rules(self):
        from tools.financial_reports.analyzer import FinancialAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics

        class FakeGenerator:
            llm_available = True
            def _call_llm(self, messages):
                raise RuntimeError("LLM 失败")

        analyzer = FinancialAnalyzer(generator=FakeGenerator())
        metrics = [FinancialMetrics(revenue=100, net_profit=50, roe=25, gross_margin=90)]
        result = analyzer.analyze("Test", metrics, ["raw"])
        # 五维评分体系下，缺少现金流和资产负债表数据会拉低综合分
        assert result.overall_health in ["优秀", "良好"]
        assert result.recommendation in ["买入", "持有"]

    def test_analyze_llm_invalid_recommendation(self):
        from tools.financial_reports.analyzer import FinancialAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics

        class FakeGenerator:
            llm_available = True
            def _call_llm(self, messages):
                return (
                    '{"overall_health": "良好", "risk_flags": [], '
                    '"strengths": [], "concerns": [], '
                    '"valuation_comment": "", '
                    '"recommendation": " INVALID ", '
                    '"summary": ""}'
                )

        analyzer = FinancialAnalyzer(generator=FakeGenerator())
        metrics = [FinancialMetrics(revenue=100)]
        result = analyzer.analyze("Test", metrics, ["raw"])
        # Invalid recommendation should be normalized to empty string
        assert result.recommendation == ""


class TestFinancialReportTool:
    def test_tool_instantiation(self):
        from tools.financial_reports import FinancialReportTool
        tool = FinancialReportTool()
        assert tool is not None
        assert hasattr(tool, "analyze")

    def test_analyze_invalid_stock(self):
        from tools.financial_reports import FinancialReportTool
        tool = FinancialReportTool()
        result = tool.analyze("INVALID_CODE_99999")
        assert "error" in result
        assert result["error"] == "Stock not found"

    def test_tool_wires_generator(self):
        from tools.financial_reports import FinancialReportTool

        class FakeGenerator:
            llm_available = True
            def _call_llm(self, messages):
                return "{}"

        tool = FinancialReportTool(generator=FakeGenerator())
        assert tool.extractor.generator is not None
        assert tool.analyzer.generator is not None

    def test_tool_wires_persona_config(self):
        from tools.financial_reports import FinancialReportTool

        class FakeConfig:
            identity = "测试身份"
            values = {"pursue": ["数据说话", "保守原则"], "reject": ["凭感觉"]}

        tool = FinancialReportTool(persona_config=FakeConfig())
        assert tool.extractor.persona_config is not None
        assert tool.analyzer.persona_config is not None
        assert tool.extractor.persona_config.identity == "测试身份"

    def test_tool_auto_loads_persona(self):
        from tools.financial_reports import FinancialReportTool
        tool = FinancialReportTool()
        # Should auto-load financial_analyst persona if available
        assert hasattr(tool, "persona_config")


def test_extractor_persona_in_prompt():
    from tools.financial_reports.extractor import PDFExtractor

    class FakeConfig:
        identity = "专业财报分析师"
        values = {"pursue": ["保守原则", "数据说话"]}

    extractor = PDFExtractor(persona_config=FakeConfig())
    prompt = extractor._build_extractor_system_prompt()
    assert "专业财报分析师" in prompt
    assert "保守原则" in prompt
    assert "数据说话" in prompt
    assert "宁可漏掉，不可错填" in prompt


def test_analyzer_persona_in_prompt():
    from tools.financial_reports.analyzer import FinancialAnalyzer

    class FakeConfig:
        identity = "资深分析师"
        values = {"pursue": ["现金流优先"], "reject": ["追涨杀跌"]}

    analyzer = FinancialAnalyzer(persona_config=FakeConfig())
    prompt = analyzer._build_analyzer_system_prompt()
    assert "资深分析师" in prompt
    assert "现金流优先" in prompt
    assert "追涨杀跌" in prompt
    assert "排雷清单" in prompt
    assert "保守原则" in prompt
    assert "宁可错过，不可踩雷" in prompt


def test_router_financial_keywords():
    from orchestration.router import Router
    router = Router()
    result = router.route("分析一下贵州茅台的财报", ["zettaranc", "financial_analyst"])
    assert result.primary == "financial_analyst"

def test_engine_query_tools_mapping():
    from orchestration.engine import OrchestrationEngine
    engine = OrchestrationEngine()
    tools = engine._get_tools_for_query("分析一下贵州茅台的财报")
    assert "financial_reports" in tools


# --------------------------------------------------------------------------- #
#  Extended schema tests (DuPont, FiveDimension, expanded FinancialMetrics)
# --------------------------------------------------------------------------- #

class TestExtendedSchemas:
    def test_expanded_financial_metrics(self):
        from tools.financial_reports.schemas import FinancialMetrics
        metrics = FinancialMetrics(
            revenue=100.0,
            roe=20.0,
            net_profit_excl_nonrecurring=45.0,
            non_recurring_income=5.0,
            accounts_receivable=15.0,
            inventory_turnover_days=60.0,
            asset_turnover=0.5,
            free_cash_flow=30.0,
            interest_bearing_debt_ratio=25.0,
            goodwill=10.0,
            current_ratio=2.5,
            quick_ratio=1.8,
            interest_coverage=8.0,
            dividend_rate=3.5,
            major_shareholder_pledge_ratio=20.0,
        )
        assert metrics.net_profit_excl_nonrecurring == 45.0
        assert metrics.accounts_receivable == 15.0
        assert metrics.interest_bearing_debt_ratio == 25.0
        assert metrics.dividend_rate == 3.5

    def test_du_pont_analysis(self):
        from tools.financial_reports.schemas import DuPontAnalysis
        dp = DuPontAnalysis(
            net_margin=15.0,
            asset_turnover=0.8,
            equity_multiplier=1.5,
            roe=18.0,
            driver="高净利率+中等杠杆",
        )
        assert dp.roe == 18.0
        assert "净利率" in dp.driver

    def test_five_dimension_scores(self):
        from tools.financial_reports.schemas import FiveDimensionScores
        scores = FiveDimensionScores(
            revenue_quality=80,
            profit_quality=75,
            cashflow_health=60,
            balance_sheet=70,
            shareholder_return=85,
            overall=74,
        )
        assert scores.overall == 74
        assert scores.revenue_quality == 80

    def test_analysis_result_with_du_pont(self):
        from tools.financial_reports.schemas import AnalysisResult, DuPontAnalysis, FiveDimensionScores
        result = AnalysisResult(
            overall_health="良好",
            du_pont=DuPontAnalysis(driver="高净利率", roe=22.0),
            five_dim_scores=FiveDimensionScores(overall=72),
        )
        assert result.du_pont.roe == 22.0
        assert result.five_dim_scores.overall == 72


class TestValuationAnalyzer:
    def test_pe_valuation_undervalued(self):
        from tools.financial_reports.valuation import ValuationAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics
        analyzer = ValuationAnalyzer()
        metrics = FinancialMetrics(eps=5.0, net_profit_yoy=20.0)
        result = analyzer.analyze(metrics, stock_price=50.0)
        assert result.pe == 10.0
        assert result.pe_judgment == "低估"  # PE=10, growth=20%, PEG=0.5

    def test_pe_valuation_overvalued(self):
        from tools.financial_reports.valuation import ValuationAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics
        analyzer = ValuationAnalyzer()
        metrics = FinancialMetrics(eps=2.0, net_profit_yoy=5.0)
        result = analyzer.analyze(metrics, stock_price=100.0)
        assert result.pe == 50.0
        assert result.pe_judgment == "高估"  # PE=50, growth=5%, PEG=10

    def test_pb_valuation_with_roe(self):
        from tools.financial_reports.valuation import ValuationAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics
        analyzer = ValuationAnalyzer()
        metrics = FinancialMetrics(roe=18.0)
        result = analyzer.analyze(
            metrics, stock_price=30.0, total_shares=10.0, net_assets=200.0
        )
        # BVPS = 200/10 = 20, PB = 30/20 = 1.5
        assert result.pb == 1.5
        assert result.pb_judgment == "合理"  # ROE=18%, PB=1.5

    def test_ps_valuation_growth(self):
        from tools.financial_reports.valuation import ValuationAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics
        analyzer = ValuationAnalyzer()
        metrics = FinancialMetrics(revenue=100.0, revenue_yoy=30.0)
        result = analyzer.analyze(
            metrics, stock_price=50.0, total_shares=10.0
        )
        # Market cap = 50*10 = 500, PS = 500/100 = 5
        assert result.ps == 5.0
        assert result.ps_judgment == "低估"  # PS=5, growth=30%, ratio=0.17 < 0.5

    def test_overall_judgment_consensus(self):
        from tools.financial_reports.valuation import ValuationAnalyzer, ValuationResult
        analyzer = ValuationAnalyzer()
        result = ValuationResult(pe_judgment="低估", pb_judgment="低估", ps_judgment="合理")
        assert analyzer._overall_valuation_judgment(result) == "整体低估"

    def test_fair_price_range(self):
        from tools.financial_reports.valuation import ValuationAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics
        analyzer = ValuationAnalyzer()
        metrics = FinancialMetrics(eps=5.0, net_profit_yoy=20.0)
        result = analyzer.analyze(metrics, stock_price=50.0)
        assert "PE法" in result.fair_price_range
        assert "元" in result.fair_price_range

    def test_valuation_comment(self):
        from tools.financial_reports.valuation import ValuationAnalyzer, ValuationResult
        analyzer = ValuationAnalyzer()
        result = ValuationResult(
            pe=15.0, pe_judgment="合理",
            pb=2.0, pb_judgment="合理",
            overall_judgment="估值合理",
            fair_price_range="PE法: 约75元",
        )
        comment = analyzer.to_valuation_comment(result)
        assert "PE: 15.0倍" in comment
        assert "估值合理" in comment
        assert "合理价格参考" in comment

    def test_insufficient_data(self):
        from tools.financial_reports.valuation import ValuationAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics
        analyzer = ValuationAnalyzer()
        metrics = FinancialMetrics()  # Empty metrics
        result = analyzer.analyze(metrics)
        assert result.overall_judgment == "数据不足，无法估值"
        comment = analyzer.to_valuation_comment(result)
        assert "缺乏估值数据" in comment


class TestAnalyzerFiveDimension:
    def test_five_dim_revenue_quality(self):
        from tools.financial_reports.analyzer import FinancialAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics
        analyzer = FinancialAnalyzer()
        # High AR ratio is a warning
        metrics = [
            FinancialMetrics(revenue=100.0, accounts_receivable=60.0),
        ]
        scores = analyzer._calculate_five_dim_scores(metrics)
        assert scores.revenue_quality < 60  # Baseline 60 minus AR penalty

    def test_five_dim_profit_quality(self):
        from tools.financial_reports.analyzer import FinancialAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics
        analyzer = FinancialAnalyzer()
        # Low nonrecurring ratio is bad
        metrics = [
            FinancialMetrics(
                net_profit=100.0,
                net_profit_excl_nonrecurring=30.0,
                gross_margin=10.0,
            ),
        ]
        scores = analyzer._calculate_five_dim_scores(metrics)
        assert scores.profit_quality < 60

    def test_five_dim_cashflow_health(self):
        from tools.financial_reports.analyzer import FinancialAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics
        analyzer = FinancialAnalyzer()
        # OCF much lower than net profit
        metrics = [
            FinancialMetrics(net_profit=100.0, operating_cash_flow=20.0),
        ]
        scores = analyzer._calculate_five_dim_scores(metrics)
        assert scores.cashflow_health < 60

    def test_five_dim_balance_sheet(self):
        from tools.financial_reports.analyzer import FinancialAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics
        analyzer = FinancialAnalyzer()
        # High debt
        metrics = [
            FinancialMetrics(interest_bearing_debt_ratio=60.0, current_ratio=1.2),
        ]
        scores = analyzer._calculate_five_dim_scores(metrics)
        assert scores.balance_sheet < 60

    def test_five_dim_shareholder_return(self):
        from tools.financial_reports.analyzer import FinancialAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics
        analyzer = FinancialAnalyzer()
        # Excellent ROE
        metrics = [
            FinancialMetrics(roe=22.0, dividend_rate=4.0),
        ]
        scores = analyzer._calculate_five_dim_scores(metrics)
        assert scores.shareholder_return > 80

    def test_du_pont_high_margin_driver(self):
        from tools.financial_reports.analyzer import FinancialAnalyzer
        from tools.financial_reports.schemas import FinancialMetrics
        analyzer = FinancialAnalyzer()
        metrics = [
            FinancialMetrics(
                net_margin=25.0, asset_turnover=0.5, debt_ratio=40.0, roe=20.0
            ),
        ]
        du_pont = analyzer._du_pont_analysis(metrics)
        assert du_pont.roe is not None
        assert "净利率" in du_pont.driver

    def test_generate_summary_includes_five_dim(self):
        from tools.financial_reports.analyzer import FinancialAnalyzer
        from tools.financial_reports.schemas import (
            FinancialMetrics, FiveDimensionScores, DuPontAnalysis,
        )
        analyzer = FinancialAnalyzer()
        metrics = [FinancialMetrics(revenue=100, net_profit=50, roe=25, gross_margin=90)]
        scores = analyzer._calculate_five_dim_scores(metrics)
        du_pont = analyzer._du_pont_analysis(metrics)
        risks = analyzer._identify_risks(metrics)
        strengths = analyzer._identify_strengths(metrics)
        concerns = analyzer._identify_concerns(metrics)
        overall = analyzer._overall_health(scores)
        valuation = analyzer._valuation_comment(metrics[-1], du_pont)
        recommendation = analyzer._recommendation(overall, risks)
        summary = analyzer._generate_summary(
            "Test", overall, scores, du_pont, risks, strengths, concerns, valuation, recommendation
        )
        assert "五维评分" in summary
        assert "杜邦分析" in summary or "ROE驱动" in summary
