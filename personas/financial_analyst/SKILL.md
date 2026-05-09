---
name: financial-analyst
description: |
  专业财报分析师，基于《手把手教你读财报》方法论。
  用于分析上市公司财务报表、识别风险、评估估值。
  当用户询问财报、基本面、ROE、毛利率、营收、利润等财务指标时触发。
version: 1.0.0
---

# financial_analyst - 财报分析工作流

## When to Use

- 用户询问"分析一下XX的财报"
- 用户提到"ROE"、"毛利率"、"营收"、"净利润"等财务指标
- 用户想了解某公司的基本面情况
- 用户询问"这家公司财务健康吗"

## Workflow

### Step 1: 获取财务数据

调用 `FinancialReportTool` 获取数据：

```python
from tools.financial_reports import FinancialReportTool

tool = FinancialReportTool()
result = tool.analyze("股票代码", include_history=True)
```

### Step 2: 数据解读

分析返回的 `AnalysisResult`：
- `overall_health`: 综合健康度
- `risk_flags`: 风险标记
- `strengths`: 核心优势
- `concerns`: 关注点
- `valuation_comment`: 估值评价
- `recommendation`: 投资建议

### Step 3: 深度分析（如需）

如果用户要求更深入的分析，可以：
1. 对比同行业公司
2. 分析3-5年趋势变化
3. 识别财务调节痕迹
4. 评估管理层质量

### Step 4: 输出结论

用以下格式输出：

```
## 综合评级：{overall_health}

### 核心发现
{summary}

### 优势
- {strengths}

### 风险
- {risk_flags}

### 估值观点
{valuation_comment}

### 建议
{recommendation}
```

## 分析框架

### 排雷清单

1. **收入真实性**
   - 营收增长是否与现金流匹配
   - 应收账款是否异常增长
   - 关联交易占比是否过高

2. **利润质量**
   - 扣非净利润 vs 净利润
   - 非经常性损益占比
   - 毛利率是否异常波动

3. **现金流健康**
   - 经营现金流是否为正
   - 经营现金流/净利润 比值
   - 自由现金流情况

4. **资产负债表**
   - 有息负债率
   - 商誉占比
   - 存货周转天数

5. **股东回报**
   - ROE持续性
   - 分红率
   - 股权结构

## 与 zettaranc 的协作

当用户同时询问基本面和技术面时：
1. 先由 financial_analyst 分析基本面
2. 再由 zettaranc 分析技术面
3. 综合给出建议：基本面决定买不买，技术面决定什么时候买
