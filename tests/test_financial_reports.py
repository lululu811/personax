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
