"""Data models for financial report tool."""

from dataclasses import dataclass, field
from typing import Optional, Literal


@dataclass
class FinancialReport:
    """Single financial report document."""
    stock_code: str
    stock_name: str
    report_type: Literal["annual", "q1", "semi", "q3"]
    year: int
    period: str
    pdf_path: str
    raw_text: str = ""


@dataclass
class FinancialMetrics:
    """Key financial metrics for a single reporting period."""
    revenue: Optional[float] = None
    revenue_yoy: Optional[float] = None
    net_profit: Optional[float] = None
    net_profit_yoy: Optional[float] = None
    roe: Optional[float] = None
    gross_margin: Optional[float] = None
    net_margin: Optional[float] = None
    debt_ratio: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    eps: Optional[float] = None


@dataclass
class AnalysisResult:
    """AI analysis result for a stock's financial health."""
    overall_health: str = ""
    risk_flags: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    valuation_comment: str = ""
    recommendation: Literal["买入", "持有", "观望", "回避", ""] = ""
    summary: str = ""
