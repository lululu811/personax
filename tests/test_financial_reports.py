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
        overall_health="",
        risk_flags=[],
        strengths=[],
        concerns=[],
        valuation_comment="",
        recommendation="",
        summary="",
    )
    assert result.risk_flags == []
    assert result.strengths == []
