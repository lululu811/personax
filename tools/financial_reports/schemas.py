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
    # --- 基础盈利指标 ---
    revenue: Optional[float] = None
    revenue_yoy: Optional[float] = None
    net_profit: Optional[float] = None
    net_profit_yoy: Optional[float] = None
    roe: Optional[float] = None
    eps: Optional[float] = None

    # --- 利润质量指标 ---
    net_profit_excl_nonrecurring: Optional[float] = None  # 扣非净利润
    non_recurring_income: Optional[float] = None           # 非经常性损益
    gross_margin: Optional[float] = None
    net_margin: Optional[float] = None
    expense_ratio: Optional[float] = None                  # 费用率

    # --- 资产效率与收入真实性 ---
    accounts_receivable: Optional[float] = None            # 应收账款
    inventory_turnover_days: Optional[float] = None        # 存货周转天数
    asset_turnover: Optional[float] = None                 # 资产周转率

    # --- 现金流指标 ---
    operating_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None                 # 自由现金流

    # --- 资产负债表安全指标 ---
    debt_ratio: Optional[float] = None                     # 资产负债率（总负债/总资产）
    interest_bearing_debt_ratio: Optional[float] = None    # 有息负债率
    goodwill: Optional[float] = None                       # 商誉
    current_ratio: Optional[float] = None                  # 流动比率
    quick_ratio: Optional[float] = None                    # 速动比率
    interest_coverage: Optional[float] = None              # 利息保障倍数

    # --- 股东回报与治理 ---
    dividend_rate: Optional[float] = None                  # 分红率/股息率
    major_shareholder_pledge_ratio: Optional[float] = None # 大股东质押比例


@dataclass
class DuPontAnalysis:
    """杜邦分析拆解结果."""
    net_margin: Optional[float] = None      # 净利率
    asset_turnover: Optional[float] = None  # 资产周转率
    equity_multiplier: Optional[float] = None  # 权益乘数
    roe: Optional[float] = None             # ROE = 净利率 × 资产周转率 × 权益乘数
    driver: str = ""                        # ROE 主要驱动因素描述


@dataclass
class FiveDimensionScores:
    """五维排雷法评分结果."""
    revenue_quality: int = 0       # 收入真实性
    profit_quality: int = 0        # 利润质量
    cashflow_health: int = 0       # 现金流健康
    balance_sheet: int = 0         # 资产负债表
    shareholder_return: int = 0    # 股东回报
    overall: int = 0               # 综合得分


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
    du_pont: DuPontAnalysis = field(default_factory=DuPontAnalysis)
    five_dim_scores: FiveDimensionScores = field(default_factory=FiveDimensionScores)
