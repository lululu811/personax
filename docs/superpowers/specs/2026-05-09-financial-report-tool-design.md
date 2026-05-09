# Financial Report Tool 设计文档

## 概述

为 personax 项目新增一个通用 tool，用于获取 A 股/港股财报数据。该 tool 能够：

1. 从巨潮资讯网 (cninfo.com.cn) 下载财报 PDF
2. 从 PDF 中提取结构化财务数据
3. 使用专业提示词进行 AI 财报分析
4. 实时返回分析结果，同时异步存入知识库

## 背景

参考项目 [CNinfo2Notebookllm](https://github.com/jarodise/CNinfo2Notebookllm) 已实现巨潮资讯网财报下载和 NotebookLM 上传功能。本设计将其核心下载逻辑复用到 personax 的 tool 体系中，并扩展结构化数据提取和 AI 分析能力。

## 需求

### 功能需求

- 支持 A 股（6 位代码）和港股（5 位代码）财报下载
- 自动下载近 5 年年报 + 当年定期报告（一季报、中报、三季报）
- 从 PDF 中提取关键财务指标（营收、净利润、ROE、毛利率等）
- 基于《手把手教你读财报》方法论进行 AI 分析
- 分析结果实时返回，数据异步存入 knowledge 系统

### 非功能需求

- 单文件下载超时 60 秒
- PDF 解析失败不阻塞其他报告处理
- 支持按股票代码或股票名称查询
- 与现有 orchestration engine 和 persona 体系集成

## 架构设计

### 目录结构

```
tools/
├── __init__.py
├── quant/                           # 现有技术指标工具
└── financial_reports/               # [新增] 财报工具
    ├── __init__.py                  # 暴露 FinancialReportTool
    ├── downloader.py                # 巨潮资讯下载器
    ├── extractor.py                 # PDF → 结构化数据提取
    ├── analyzer.py                  # AI 财报分析
    └── schemas.py                   # 数据模型

personas/
├── __init__.py
├── persona_loader.py
├── zettaranc/
└── financial_analyst/               # [新增] 财务分析师 persona
    ├── personality.md               # 角色设定
    └── SKILL.md                     # 工作流和指令
```

### 核心数据模型

```python
@dataclass
class FinancialReport:
    """单份财报报告"""
    stock_code: str           # 股票代码
    stock_name: str           # 股票名称
    report_type: str          # annual | q1 | semi | q3
    year: int
    period: str               # 2024年度 | 2024Q1
    pdf_path: str             # 本地 PDF 路径
    raw_text: str             # PDF 提取的原始文本

@dataclass
class FinancialMetrics:
    """关键财务指标（单期）"""
    revenue: Optional[float]           # 营业收入
    revenue_yoy: Optional[float]       # 营收同比增长率
    net_profit: Optional[float]        # 净利润
    net_profit_yoy: Optional[float]    # 净利润同比增长率
    roe: Optional[float]               # 净资产收益率
    gross_margin: Optional[float]      # 毛利率
    net_margin: Optional[float]        # 净利率
    debt_ratio: Optional[float]        # 资产负债率
    operating_cash_flow: Optional[float]   # 经营现金流
    eps: Optional[float]               # 每股收益

@dataclass
class AnalysisResult:
    """AI 分析结果"""
    overall_health: str       # 综合健康度：优秀/良好/一般/差
    risk_flags: list[str]     # 风险标记列表
    strengths: list[str]      # 优势分析
    concerns: list[str]       # 关注点
    valuation_comment: str    # 估值评价
    recommendation: str       # 建议：买入/持有/观望/回避
    summary: str              # 分析摘要
```

### 工具类设计

```python
class FinancialReportTool:
    """财报获取与分析工具

    Usage:
        tool = FinancialReportTool()
        result = tool.analyze("600519", include_history=True)
        print(result.analysis.recommendation)
    """

    def __init__(self):
        self.downloader = CnInfoDownloader()
        self.extractor = PDFExtractor()
        self.analyzer = FinancialAnalyzer()

    def analyze(
        self,
        stock_input: str,
        include_history: bool = True,
        output_dir: Optional[str] = None,
    ) -> dict:
        """分析指定股票的财报

        Args:
            stock_input: 股票代码或名称（如 600519 或 贵州茅台）
            include_history: 是否包含近5年年报（False则只下载最新一期）
            output_dir: PDF 保存目录（默认创建临时目录）

        Returns:
            {
                "stock_code": str,
                "stock_name": str,
                "market": str,              # szse | hke
                "reports": list[FinancialReport],
                "metrics": list[FinancialMetrics],  # 逐年数据
                "analysis": AnalysisResult,
                "pdf_paths": list[str],
                "errors": list[str],        # 非致命错误记录
            }
        """
```

## 数据流

```
用户查询："分析一下贵州茅台的财报"
        ↓
Orchestration Engine 路由到 financial_analyst persona
        ↓
调用 FinancialReportTool.analyze("600519")
        ↓
┌─────────────────────────────────────────┐
│ Step 1: Downloader                       │
│  - 查找股票代码和市场                      │
│  - 下载近5年年报 + 当年定期报告            │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ Step 2: Extractor                        │
│  - PDF 解析（pdfplumber / PyPDF2）        │
│  - LLM 提取结构化指标（revenue, roe...）   │
│  - 构建 FinancialMetrics 列表             │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ Step 3: Analyzer                         │
│  - 载入 financial_analyst_prompt         │
│  - LLM 分析：排雷 → 估值 → 建议           │
│  - 输出 AnalysisResult                   │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ Step 4: 返回 + 异步存储                   │
│  - 同步返回完整结果给调用方                │
│  - 异步：metrics 存入 knowledge store      │
│  - 异步：PDF 元数据记录到 knowledge        │
└─────────────────────────────────────────┘
```

## 模块详细设计

### downloader.py

复用 CNinfo2Notebookllm 的核心逻辑：

- `CnInfoDownloader` 类
  - `find_stock(stock_input)` → 按代码或名称查找股票，返回 (code, info, market)
  - `download_annual_reports(stock_code, years, output_dir, market)` → 下载年报
  - `download_periodic_reports(stock_code, year, output_dir, market)` → 下载定期报告
  - `_query_announcements(filter_params, market)` → 调用 cninfo API
  - `_download_pdf(announcement, output_dir)` → 下载单个 PDF

**关键实现细节**：
- A 股和港股的 API 参数不同（category、searchkey、column）
- 年报搜索时段：A 股次年 3-6 月，港股当年 1-6 月
- 港股需过滤掉 A 股子公司的报告

### extractor.py

```python
class PDFExtractor:
    def extract(self, pdf_path: str) -> tuple[str, dict]:
        """提取 PDF 内容

        Returns:
            (raw_text, structured_metrics)
            raw_text: PDF 全文文本
            structured_metrics: 提取的关键指标字典
        """
```

**提取策略**：
1. 先用 pdfplumber 提取表格和文本
2. 关键财务数据表格通常在前 20 页
3. 使用 LLM（Claude API）从 raw_text 中提取结构化指标
4. 回退：如果 LLM 提取失败，保留 raw_text 供人工查看

### analyzer.py

```python
class FinancialAnalyzer:
    def analyze(
        self,
        stock_name: str,
        metrics_history: list[FinancialMetrics],
        raw_reports: list[str],
    ) -> AnalysisResult:
        """基于财务指标历史进行 AI 分析"""
```

**分析 prompt 结构**：
1. System prompt: `assets/financial_analyst_prompt.txt`（《手把手教你读财报》方法论）
2. User prompt: 包含多年财务指标对比数据
3. Output format: 强制 JSON 格式返回 AnalysisResult 字段

## 与现有系统集成

### Orchestration Engine

在 `orchestration/engine.py` 中：

1. **QUERY_TOOLS** 添加映射：
   ```python
   QUERY_TOOLS = {
       # ... 现有工具 ...
       "财报": ["financial_reports"],
       "年报": ["financial_reports"],
       "财务": ["financial_reports"],
       "基本面": ["financial_reports"],
   }
   ```

2. **_compute_tool** 添加工具映射：
   ```python
   from tools.financial_reports import FinancialReportTool
   TOOL_MAP = {
       # ... 现有工具 ...
       "financial_reports": FinancialReportTool(),
   }
   ```

3. **Router** 中新增 persona 路由：
   ```python
   KEYWORD_PERSONAS = {
       # ... 现有映射 ...
       "财报": "financial_analyst",
       "年报": "financial_analyst",
       "财务": "financial_analyst",
       "基本面": "financial_analyst",
       "ROE": "financial_analyst",
       "估值": "financial_analyst",
   }
   ```

### Knowledge 系统

在 `tools/financial_reports/__init__.py` 中：

```python
def _store_async(self, stock_code: str, metrics: list[FinancialMetrics]):
    """异步将财务指标存入 knowledge store"""
    try:
        from knowledge.store import store_document
        doc = {
            "type": "financial_metrics",
            "stock_code": stock_code,
            "metrics": [m.__dict__ for m in metrics],
            "timestamp": datetime.now().isoformat(),
        }
        store_document(f"financial_metrics_{stock_code}", doc)
    except Exception:
        # 存储失败不阻塞主流程
        pass
```

### Persona 系统

新增 `personas/financial_analyst/`：

- `personality.md`: 角色性格设定（专业、谨慎、数据驱动）
- `SKILL.md`: 工作流指令
  - 财报排雷流程
  - 估值分析方法
  - 与技术指标 persona（zettaranc）的协作边界

## 错误处理策略

| 场景 | 严重程度 | 处理方式 |
|------|----------|----------|
| 股票代码无效 | 致命 | 返回 `{"error": "Stock not found"}` |
| cninfo API 限流 | 警告 | 指数退避重试 3 次，失败则跳过 |
| 单份 PDF 下载失败 | 警告 | 记录错误，继续处理其他报告 |
| PDF 解析失败 | 警告 | 保留文件路径，跳过提取 |
| LLM 提取超时 | 警告 | 返回 raw_text，标记 `extracted=False` |
| knowledge 存储失败 | 信息 | 记录日志，不影响返回结果 |

## 依赖

```
# 现有依赖（已安装）
pandas
httpx

# 新增依赖
pdfplumber>=0.11.0      # PDF 解析
pypdf>=4.0.0            # PDF 备选解析
```

## 测试策略

1. **单元测试**：测试 `CnInfoDownloader.find_stock()` 的股票查找逻辑
2. **集成测试**：测试完整 `analyze()` 流程（mock cninfo API）
3. **端到端测试**：使用真实股票代码（如 600519）测试下载和提取

## 未来扩展

1. **数据源扩展**：支持东方财富、同花顺等更多数据源
2. **对比分析**：支持两家公司的财务指标对比
3. **历史趋势**：自动生成多年指标的图表趋势
4. **实时数据**：接入实时行情数据与财报数据交叉分析

## 参考

- 参考项目：[CNinfo2Notebookllm](https://github.com/jarodise/CNinfo2Notebookllm)
- 巨潮资讯网 API: http://www.cninfo.com.cn
- 分析方法论：《手把手教你读财报》
