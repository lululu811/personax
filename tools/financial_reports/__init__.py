"""Financial Report Tool - Download, extract, and analyze stock financial reports."""

import asyncio
import os
import re
import tempfile
from datetime import datetime
from typing import Optional

from tools.financial_reports.schemas import (
    AnalysisResult,
    FinancialMetrics,
    FinancialReport,
)
from tools.financial_reports.downloader import CnInfoDownloader
from tools.financial_reports.extractor import PDFExtractor
from tools.financial_reports.analyzer import FinancialAnalyzer

__all__ = [
    "FinancialReport",
    "FinancialMetrics",
    "AnalysisResult",
    "FinancialReportTool",
]


class FinancialReportTool:
    """Unified tool to download, extract, and analyze stock financial reports."""

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
        """Main entry point: analyze a stock's financial reports.

        Args:
            stock_input: Stock code or name.
            include_history: Whether to download last 5 years of annual reports.
            output_dir: Directory to save PDFs; uses temp dir if None.

        Returns:
            Result dict with stock info, reports, metrics, analysis, errors.
        """
        # 1. Find stock
        stock_code, stock_info, market = self.downloader.find_stock(stock_input)
        if stock_code is None:
            return {"error": "Stock not found"}

        stock_name = stock_info.get("zwjc", stock_code)

        # 2. Create output directory
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="fin_report_")
        os.makedirs(output_dir, exist_ok=True)

        pdf_paths: list[str] = []
        reports: list[FinancialReport] = []
        metrics_history: list[FinancialMetrics] = []
        errors: list[str] = []
        raw_texts: list[str] = []

        current_year = datetime.now().year

        try:
            # 3. Download reports
            if include_history:
                # Last 5 years annual reports
                years = list(range(current_year - 5, current_year))
                annual_pdfs = self.downloader.download_annual_reports(
                    stock_code, years, output_dir, market
                )
                pdf_paths.extend(annual_pdfs)

            # Current year periodic reports
            periodic_pdfs = self.downloader.download_periodic_reports(
                stock_code, current_year, output_dir, market
            )
            pdf_paths.extend(periodic_pdfs)

            # 4. Extract text and metrics from each PDF
            for pdf_path in pdf_paths:
                try:
                    raw_text, metrics = self.extractor.extract(pdf_path)
                    raw_texts.append(raw_text)

                    report_type, year = self._infer_report_meta(pdf_path)
                    period = self._build_period(report_type, year)

                    report = FinancialReport(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        report_type=report_type,
                        year=year,
                        period=period,
                        pdf_path=pdf_path,
                        raw_text=raw_text,
                    )
                    reports.append(report)
                    metrics_history.append(metrics)
                except Exception as e:
                    errors.append(f"Extraction failed for {pdf_path}: {e}")

            # 5. Analyze
            if metrics_history:
                analysis = self.analyzer.analyze(
                    stock_name, metrics_history, raw_texts
                )
            else:
                analysis = AnalysisResult(
                    overall_health="未知",
                    summary=f"未能提取{stock_name}的有效财务指标，无法进行分析。",
                )

            # 6. Async knowledge storage (best effort)
            try:
                self._store_async(stock_code, stock_name, metrics_history, reports)
            except Exception:
                pass  # Best effort, ignore failures

            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "market": market,
                "reports": reports,
                "metrics": metrics_history,
                "analysis": analysis,
                "pdf_paths": pdf_paths,
                "errors": errors,
            }

        except Exception as e:
            errors.append(str(e))
            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "market": market,
                "reports": reports,
                "metrics": metrics_history,
                "analysis": AnalysisResult(
                    overall_health="未知",
                    summary=f"分析过程出错: {e}",
                ),
                "pdf_paths": pdf_paths,
                "errors": errors,
            }

    def _infer_report_meta(self, pdf_path: str) -> tuple[str, int]:
        """Infer report type and year from PDF filename.

        Returns:
            (report_type, year) where report_type is one of
            'annual', 'q1', 'semi', 'q3'.
        """
        filename = os.path.basename(pdf_path)

        # Extract year from filename (4-digit number)
        year_match = re.search(r"(20\d{2})", filename)
        year = int(year_match.group(1)) if year_match else datetime.now().year

        # Determine report type from keywords in filename
        if "半年度" in filename or "中期" in filename:
            report_type = "semi"
        elif "一季度" in filename or "第一季度" in filename or "Q1" in filename.upper():
            report_type = "q1"
        elif "三季度" in filename or "第三季度" in filename or "Q3" in filename.upper():
            report_type = "q3"
        else:
            report_type = "annual"

        return report_type, year

    def _build_period(self, report_type: str, year: int) -> str:
        """Build human-readable period string."""
        if report_type == "annual":
            return f"{year}年度"
        elif report_type == "q1":
            return f"{year}Q1"
        elif report_type == "semi":
            return f"{year}半年度"
        elif report_type == "q3":
            return f"{year}Q3"
        return f"{year}"

    def _store_async(
        self,
        stock_code: str,
        stock_name: str,
        metrics: list[FinancialMetrics],
        reports: list[FinancialReport],
    ) -> None:
        """Asynchronously store financial metrics to knowledge base.

        Best-effort: failures are silently ignored to not block main flow.
        """
        try:
            from knowledge.store import store_document

            doc = {
                "type": "financial_metrics",
                "stock_code": stock_code,
                "stock_name": stock_name,
                "metrics": [
                    {k: v for k, v in m.__dict__.items() if v is not None}
                    for m in metrics
                ],
                "report_count": len(reports),
                "timestamp": datetime.now().isoformat(),
            }
            store_document(f"financial_metrics_{stock_code}", doc)
        except Exception:
            # Knowledge storage is optional; don't fail the main request
            pass
