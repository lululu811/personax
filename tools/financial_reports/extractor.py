"""Extract structured financial data from PDF reports."""

import json
import os
import re
from typing import Optional

import pdfplumber

from tools.financial_reports.schemas import FinancialMetrics


class PDFExtractor:
    """Extract text and structured metrics from financial report PDFs."""

    def __init__(self, generator=None, persona_config=None):
        self.generator = generator
        self.persona_config = persona_config

    def extract(self, pdf_path: str) -> tuple[str, FinancialMetrics]:
        """Extract text and financial metrics from a PDF.

        Tries LLM extraction first (if generator is available), then
        falls back to regex-based extraction.
        """
        if not os.path.exists(pdf_path):
            return "", FinancialMetrics()

        raw_text = self._extract_text(pdf_path)

        # Try LLM extraction first
        if self.generator is not None and getattr(self.generator, "llm_available", False):
            try:
                metrics = self._extract_metrics_with_llm(raw_text)
                if self._has_any_value(metrics):
                    return raw_text, metrics
            except Exception:
                pass  # Fall through to regex fallback

        metrics = self._extract_metrics_from_text(raw_text)
        return raw_text, metrics

    def _extract_text(self, pdf_path: str) -> str:
        """Extract raw text from PDF using pdfplumber (first 30 pages)."""
        text_parts = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages[:30]:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
        except Exception:
            return ""
        return self._clean_text("\n".join(text_parts))

    def _clean_text(self, text: str) -> str:
        """Clean extracted text - remove excessive whitespace."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  LLM extraction with persona prompt
    # ------------------------------------------------------------------ #

    def _extract_metrics_with_llm(self, text: str) -> FinancialMetrics:
        """Use LLM to extract structured financial metrics from text.

        Injects persona principles (data-driven, conservative) into the prompt.
        """
        system_prompt = self._build_extractor_system_prompt()
        user_prompt = self._build_extraction_prompt(text)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = self.generator._call_llm(messages)
        return self._parse_metrics_from_llm_response(response)

    def _build_extractor_system_prompt(self) -> str:
        """Build system prompt for LLM extraction, infused with persona DNA."""
        lines = [
            "你是一位专业的财报数据提取助手，基于《手把手教你读财报》的方法论。",
            "",
            "【核心原则】",
            "1. 数据说话：所有判断必须基于财报文本中的明确数字，不凭感觉",
            "2. 保守原则：宁可漏掉，不可错填。找不到的指标明确返回 null，绝不编造",
            "3. 精确提取：注意单位换算（万元→亿元除以10000，元→亿元除以100000000）",
            "4. 百分比处理：百分比直接返回数值，如 25.5 表示 25.5%",
            "",
            "【输出要求】",
            "- 只返回 JSON，不要任何解释或 markdown 代码块",
            "- 确保所有数值都是数字类型，不要用字符串",
        ]

        # Inject persona identity if available
        if self.persona_config is not None:
            identity = getattr(self.persona_config, "identity", "")
            if identity:
                lines.insert(0, f"【身份】{identity}")
                lines.insert(1, "")

            values = getattr(self.persona_config, "values", {})
            if values.get("pursue"):
                lines.append("")
                lines.append("【价值观驱动】")
                for pursuit in values["pursue"][:3]:
                    lines.append(f"- {pursuit}")

        return "\n".join(lines)

    def _build_extraction_prompt(self, text: str) -> str:
        """Build the extraction prompt for LLM."""
        # Limit text length to avoid token overflow
        truncated = text[:12000]

        prompt = (
            "请从以下财报文本中提取关键财务指标。\n\n"
            "规则：\n"
            "1. 金额单位为 亿元（原文中的万元请除以 10000，元请除以 100000000）\n"
            "2. 百分比直接返回数值，如 25.5 表示 25.5%\n"
            "3. 如果某项指标在文本中找不到，返回 null\n"
            "4. 只返回 JSON，不要任何解释\n\n"
            "返回格式（找不到的字段填 null）：\n"
            "{\n"
            '  "revenue": 营业收入（亿元）,\n'
            '  "revenue_yoy": 营收同比增长率（%）,\n'
            '  "net_profit": 净利润（亿元）,\n'
            '  "net_profit_yoy": 净利润同比增长率（%）,\n'
            '  "eps": 基本每股收益（元）,\n'
            '  "net_profit_excl_nonrecurring": 扣除非经常性损益后的净利润（亿元）,\n'
            '  "non_recurring_income": 非经常性损益（亿元）,\n'
            '  "gross_margin": 毛利率（%）,\n'
            '  "net_margin": 净利率（%）,\n'
            '  "expense_ratio": 费用率（销售费用+管理费用+财务费用）/ 营收（%）,\n'
            '  "accounts_receivable": 应收账款（亿元）,\n'
            '  "inventory_turnover_days": 存货周转天数（天）,\n'
            '  "asset_turnover": 总资产周转率（次）,\n'
            '  "operating_cash_flow": 经营活动现金流净额（亿元）,\n'
            '  "free_cash_flow": 自由现金流（经营现金流 - 资本支出）（亿元）,\n'
            '  "debt_ratio": 资产负债率（%）,\n'
            '  "interest_bearing_debt_ratio": 有息负债率（有息负债/总资产）（%）,\n'
            '  "goodwill": 商誉（亿元）,\n'
            '  "current_ratio": 流动比率（流动资产/流动负债）,\n'
            '  "quick_ratio": 速动比率（速动资产/流动负债）,\n'
            '  "interest_coverage": 利息保障倍数（息税前利润/利息费用）,\n'
            '  "dividend_rate": 分红率（现金分红/净利润）或股息率（%）,\n'
            '  "major_shareholder_pledge_ratio": 大股东质押比例（%）\n'
            "}\n\n"
            "财报文本：\n"
            f"{truncated}"
        )
        return prompt

    def _parse_metrics_from_llm_response(self, response: str) -> FinancialMetrics:
        """Parse JSON response from LLM into FinancialMetrics."""
        # Strip markdown code fences if present
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)

        def to_float(val):
            if val is None or val == "":
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        return FinancialMetrics(
            revenue=to_float(data.get("revenue")),
            revenue_yoy=to_float(data.get("revenue_yoy")),
            net_profit=to_float(data.get("net_profit")),
            net_profit_yoy=to_float(data.get("net_profit_yoy")),
            roe=to_float(data.get("roe")),
            eps=to_float(data.get("eps")),
            net_profit_excl_nonrecurring=to_float(data.get("net_profit_excl_nonrecurring")),
            non_recurring_income=to_float(data.get("non_recurring_income")),
            gross_margin=to_float(data.get("gross_margin")),
            net_margin=to_float(data.get("net_margin")),
            expense_ratio=to_float(data.get("expense_ratio")),
            accounts_receivable=to_float(data.get("accounts_receivable")),
            inventory_turnover_days=to_float(data.get("inventory_turnover_days")),
            asset_turnover=to_float(data.get("asset_turnover")),
            operating_cash_flow=to_float(data.get("operating_cash_flow")),
            free_cash_flow=to_float(data.get("free_cash_flow")),
            debt_ratio=to_float(data.get("debt_ratio")),
            interest_bearing_debt_ratio=to_float(data.get("interest_bearing_debt_ratio")),
            goodwill=to_float(data.get("goodwill")),
            current_ratio=to_float(data.get("current_ratio")),
            quick_ratio=to_float(data.get("quick_ratio")),
            interest_coverage=to_float(data.get("interest_coverage")),
            dividend_rate=to_float(data.get("dividend_rate")),
            major_shareholder_pledge_ratio=to_float(data.get("major_shareholder_pledge_ratio")),
        )

    def _has_any_value(self, metrics: FinancialMetrics) -> bool:
        """Check if any metric field has a non-None value."""
        return any(
            v is not None
            for v in metrics.__dict__.values()
        )

    # ------------------------------------------------------------------ #
    #  Regex fallback (unchanged)
    # ------------------------------------------------------------------ #

    def _extract_metrics_from_text(self, text: str) -> FinancialMetrics:
        """Extract structured financial metrics using regex patterns."""
        metrics = FinancialMetrics()

        # Revenue
        metrics.revenue = self._find_first_number(text, [
            r"营业收入[\s:：]+([\d,\.]+)",
            r"营业总收入[\s:：]+([\d,\.]+)",
        ])

        # Net profit
        metrics.net_profit = self._find_first_number(text, [
            r"归属于母公司股东的净利润[\s:：]+([\d,\.]+)",
            r"净利润[\s:：]+([\d,\.]+)",
        ])

        # ROE
        metrics.roe = self._find_first_number(text, [
            r"加权平均净资产收益率[\s:：]+([\d,\.]+)",
            r"净资产收益率[\s:：]+([\d,\.]+)",
        ])

        # Gross margin
        metrics.gross_margin = self._find_first_number(text, [
            r"毛利率[\s:：]+([\d,\.]+)",
        ])

        # Net margin
        metrics.net_margin = self._find_first_number(text, [
            r"净利率[\s:：]+([\d,\.]+)",
        ])

        # Debt ratio
        metrics.debt_ratio = self._find_first_number(text, [
            r"资产负债率[\s:：]+([\d,\.]+)",
        ])

        # Operating cash flow
        metrics.operating_cash_flow = self._find_first_number(text, [
            r"经营活动产生的现金流量净额[\s:：]+([\d,\.]+)",
            r"经营现金流[\s:：]+([\d,\.]+)",
        ])

        # EPS
        metrics.eps = self._find_first_number(text, [
            r"基本每股收益[\s:：]+([\d,\.]+)",
            r"每股收益[\s:：]+([\d,\.]+)",
        ])

        # 扣非净利润
        metrics.net_profit_excl_nonrecurring = self._find_first_number(text, [
            r"扣除非经常性损益后的净利润[\s:：]+([\d,\.]+)",
            r"扣非净利润[\s:：]+([\d,\.]+)",
        ])

        # 非经常性损益
        metrics.non_recurring_income = self._find_first_number(text, [
            r"非经常性损益[\s:：]+([\d,\.]+)",
        ])

        # 费用率
        metrics.expense_ratio = self._find_first_number(text, [
            r"费用率[\s:：]+([\d,\.]+)",
            r"期间费用率[\s:：]+([\d,\.]+)",
        ])

        # 应收账款
        metrics.accounts_receivable = self._find_first_number(text, [
            r"应收账款[\s:：]+([\d,\.]+)",
        ])

        # 存货周转天数
        metrics.inventory_turnover_days = self._find_first_number(text, [
            r"存货周转天数[\s:：]+([\d,\.]+)",
        ])

        # 资产周转率
        metrics.asset_turnover = self._find_first_number(text, [
            r"总资产周转率[\s:：]+([\d,\.]+)",
        ])

        # 自由现金流
        metrics.free_cash_flow = self._find_first_number(text, [
            r"自由现金流[\s:：]+([\d,\.]+)",
        ])

        # 有息负债率
        metrics.interest_bearing_debt_ratio = self._find_first_number(text, [
            r"有息负债率[\s:：]+([\d,\.]+)",
        ])

        # 商誉
        metrics.goodwill = self._find_first_number(text, [
            r"商誉[\s:：]+([\d,\.]+)",
        ])

        # 流动比率
        metrics.current_ratio = self._find_first_number(text, [
            r"流动比率[\s:：]+([\d,\.]+)",
        ])

        # 速动比率
        metrics.quick_ratio = self._find_first_number(text, [
            r"速动比率[\s:：]+([\d,\.]+)",
        ])

        # 利息保障倍数
        metrics.interest_coverage = self._find_first_number(text, [
            r"利息保障倍数[\s:：]+([\d,\.]+)",
        ])

        # 分红率/股息率
        metrics.dividend_rate = self._find_first_number(text, [
            r"分红率[\s:：]+([\d,\.]+)",
            r"股息率[\s:：]+([\d,\.]+)",
        ])

        # 大股东质押比例
        metrics.major_shareholder_pledge_ratio = self._find_first_number(text, [
            r"大股东质押比例[\s:：]+([\d,\.]+)",
        ])

        return metrics

    def _find_first_number(self, text: str, patterns: list[str]) -> Optional[float]:
        """Find first matching number in text using regex patterns."""
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1).replace(",", ""))
                except (ValueError, IndexError):
                    continue
        return None
