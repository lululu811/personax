"""Extract structured financial data from PDF reports."""

import os
import re
from typing import Optional

import pdfplumber

from tools.financial_reports.schemas import FinancialMetrics


class PDFExtractor:
    """Extract text and structured metrics from financial report PDFs."""

    def extract(self, pdf_path: str) -> tuple[str, FinancialMetrics]:
        """Extract text and financial metrics from a PDF."""
        if not os.path.exists(pdf_path):
            return "", FinancialMetrics()

        raw_text = self._extract_text(pdf_path)
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
