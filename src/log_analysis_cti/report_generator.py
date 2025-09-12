"""
Advanced report generation module for log analysis and CTI results.
- Safe defaults (no KeyError)
- Rich console summary with colors and ASCII bars
- Excel: conditional formatting + autosize
- PDF/DOCX/Markdown: optional charts embedded (generated via matplotlib)
- New: single-file HTML report with inline CSS and base64 images
- JSON/Text: unchanged but hardened
"""

from __future__ import annotations

import os
import io
import json
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from colorama import Fore, Style
from tabulate import tabulate

# Optional deps are guarded so the module degrades gracefully.
try:
    import pandas as pd  # noqa: F401
except Exception:
    pd = None  # type: ignore

try:
    import openpyxl  # noqa: F401
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.formatting.rule import ColorScaleRule, CellIsRule
except Exception:
    openpyxl = None  # type: ignore

try:
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
except Exception:
    Document = None  # type: ignore

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
except Exception:
    SimpleDocTemplate = None  # type: ignore

try:
    # Charts are optional; we only import if available.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:
    plt = None  # type: ignore


# ------------------------- Utility helpers -------------------------

def _ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _safe_get(d: Dict[str, Any], path: List[str], default: Any = 0) -> Any:
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _bar(count: int, total: int, width: int = 24, fill_char: str = "█") -> str:
    if total <= 0:
        return ""
    ratio = max(0.0, min(1.0, count / float(total)))
    filled = int(round(ratio * width))
    return fill_char * filled + " " * (width - filled)


def _pct(count: int, total: int) -> float:
    return 0.0 if total <= 0 else (100.0 * count / float(total))


def _as_base64_png(fig) -> str:
    """Convert a Matplotlib figure to base64 PNG (no filesystem write)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


# ------------------------- Main Report Generator -------------------------

class ReportGenerator:
    """Generates comprehensive reports from log analysis and CTI data."""

    def __init__(self, output_dir: str = None):
        # Default to project-level out/reports if not provided
        if output_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            output_dir = os.path.join(project_root, "out", "reports")
        self.output_dir = output_dir
        _ensure_dir(self.output_dir)

    # ----------- Public: Simple file types -----------

    def generate_comprehensive_report(
        self,
        log_stats: Dict[str, Any],
        enriched_data: Dict[str, Dict[str, Any]],
        cti_stats: Dict[str, Any],
        filename: Optional[str] = None,
        map_image_path: Optional[str] = None,
        history_data: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """(TXT) Convenience wrapper matching your original function with map and history."""
        if not filename:
            filename = f"log_analysis_cti_report_{_now_stamp()}.txt"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self._generate_report_text(log_stats, enriched_data, cti_stats, map_image_path, history_data))
        print(f"{Fore.GREEN}Report generated: {filepath}{Style.RESET_ALL}")
        return filepath

    def generate_text_report(
        self,
        log_stats: Dict[str, Any],
        enriched_data: Dict[str, Dict[str, Any]],
        cti_stats: Dict[str, Any],
        file_path: str,
        tab_data: Optional[Dict[str, Any]] = None,
        map_image_path: Optional[str] = None,
        history_data: Optional[List[Dict[str, Any]]] = None
    ):
        """Plain text report (same as 'comprehensive', but with explicit path)."""
        try:
            content = self._generate_report_text(log_stats, enriched_data, cti_stats, tab_data, map_image_path, history_data)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"{Fore.GREEN}Text report generated: {file_path}{Style.RESET_ALL}")
        except Exception as e:
            raise Exception(f"Failed to generate text report: {str(e)}")

    def generate_json_report(
        self,
        log_stats: Dict[str, Any],
        enriched_data: Dict[str, Dict[str, Any]],
        cti_stats: Dict[str, Any],
        filename: Optional[str] = None
    ) -> str:
        if not filename:
            filename = f"log_analysis_cti_report_{_now_stamp()}.json"
        filepath = os.path.join(self.output_dir, filename)
        report_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "tool_version": "1.2.0",
                "report_type": "log_analysis_cti"
            },
            "log_statistics": log_stats,
            "cti_statistics": cti_stats,
            "enriched_ip_data": enriched_data
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        print(f"{Fore.GREEN}JSON report generated: {filepath}{Style.RESET_ALL}")
        return filepath

    # ----------- Public: Markdown / HTML -----------

    def generate_markdown_report(
        self,
        log_stats: Dict[str, Any],
        enriched_data: Dict[str, Dict[str, Any]],
        cti_stats: Dict[str, Any],
        file_path: str,
        tab_data: Optional[Dict[str, Any]] = None,
        embed_charts: bool = True
    ):
        try:
            chart_b64 = {}
            if embed_charts and plt is not None:
                chart_b64 = self._render_charts_b64(log_stats, cti_stats)
            content = self._generate_markdown_content(log_stats, enriched_data, cti_stats, tab_data, chart_b64)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"{Fore.GREEN}Markdown report generated: {file_path}{Style.RESET_ALL}")
        except Exception as e:
            raise Exception(f"Failed to generate Markdown report: {str(e)}")

    def generate_html_report(
        self,
        log_stats: Dict[str, Any],
        enriched_data: Dict[str, Dict[str, Any]],
        cti_stats: Dict[str, Any],
        file_path: str,
        tab_data: Optional[Dict[str, Any]] = None,
        embed_charts: bool = True
    ):
        """New: single-file HTML with inline CSS + base64 charts."""
        try:
            chart_b64 = {}
            if embed_charts and plt is not None:
                chart_b64 = self._render_charts_b64(log_stats, cti_stats)

            html = self._generate_html_content(log_stats, enriched_data, cti_stats, tab_data, chart_b64)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"{Fore.GREEN}HTML report generated: {file_path}{Style.RESET_ALL}")
        except Exception as e:
            raise Exception(f"Failed to generate HTML report: {str(e)}")

    # ----------- Public: DOCX / PDF -----------

    def generate_docx_report(
        self,
        log_stats: Dict[str, Any],
        enriched_data: Dict[str, Dict[str, Any]],
        cti_stats: Dict[str, Any],
        file_path: str,
        tab_data: Optional[Dict[str, Any]] = None,
        embed_charts: bool = True
    ):
        if Document is None:
            raise Exception("python-docx is required. Install with: pip install python-docx")
        try:
            doc = Document()
            title = doc.add_heading("CTI Analysis Report", 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p = doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            doc.add_paragraph()

            # Executive summary table
            doc.add_heading("Executive Summary", level=1)
            summary_rows = self._summary_kv_rows(log_stats, cti_stats)
            table = doc.add_table(rows=len(summary_rows), cols=2)
            table.style = "Table Grid"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            for i, (k, v) in enumerate(summary_rows):
                table.cell(i, 0).text = str(k)
                table.cell(i, 1).text = str(v)
                if i == 0:
                    for cell in table.rows[i].cells:
                        if cell.paragraphs[0].runs:
                            cell.paragraphs[0].runs[0].bold = True
            doc.add_paragraph()

            # Optional charts
            chart_paths = {}
            if embed_charts and plt is not None:
                chart_paths = self._render_charts_files(cti_stats, log_stats)

            for path in chart_paths.values():
                try:
                    doc.add_picture(path, width=Inches(6.5))
                    doc.add_paragraph()

                except Exception:
                    # ignore if image loading fails
                    pass

            # IP details (compact)
            doc.add_heading("IP Analysis Details", level=1)
            headers = ["IP Address", "Threat Level", "Risk Score", "Abuse Confidence", "VT Reputation"]
            ip_table = doc.add_table(rows=1, cols=len(headers))
            ip_table.style = "Table Grid"
            for i, h in enumerate(headers):
                ip_table.cell(0, i).text = h
                if ip_table.cell(0, i).paragraphs[0].runs:
                    ip_table.cell(0, i).paragraphs[0].runs[0].bold = True

            for ip, data in enriched_data.items():
                vt = data.get("virustotal", {}) or {}
                ab = data.get("abuseipdb", {}) or {}
                row = ip_table.add_row().cells
                row[0].text = ip
                row[1].text = str(data.get("overall_threat_level", "unknown"))
                row[2].text = str(data.get("risk_score", 0))
                row[3].text = str(ab.get("abuse_confidence", "N/A"))
                row[4].text = str(vt.get("reputation", "N/A"))

            # Add AI Analysis sections
            if tab_data and 'ai_comprehensive_report' in tab_data:
                ai_report = tab_data['ai_comprehensive_report']
                if ai_report:
                    doc.add_heading("AI Comprehensive Analysis", level=1)
                    doc.add_paragraph(ai_report)
                    doc.add_paragraph()
            
            if tab_data and 'ai_output' in tab_data:
                ai_output = tab_data['ai_output']
                if ai_output:
                    doc.add_heading("AI Detailed Analysis", level=1)
                    doc.add_paragraph(ai_output)
                    doc.add_paragraph()
            
            if tab_data and 'statistics_data' in tab_data:
                stats_data = tab_data['statistics_data']
                ai_summary = stats_data.get('ai_summary', '')
                if ai_summary:
                    doc.add_heading("Statistics Summary", level=1)
                    doc.add_paragraph(ai_summary)
                    doc.add_paragraph()
            
            if tab_data and 'map_data' in tab_data:
                map_data = tab_data['map_data']
                if map_data.get('markers'):
                    doc.add_heading("Geographic Analysis", level=1)
                    doc.add_paragraph(f"Total IPs Mapped: {map_data.get('total_markers', 0)}")
                    doc.add_paragraph("IP Geographic Distribution:")
                    for marker in map_data.get('markers', []):
                        doc.add_paragraph(f"• {marker.get('ip', '')} - Threat: {marker.get('threat_level', '')} - Risk: {marker.get('risk_score', 0)}%")
                    doc.add_paragraph()

            doc.save(file_path)
            print(f"{Fore.GREEN}Word document generated: {file_path}{Style.RESET_ALL}")
        except Exception as e:
            raise Exception(f"Failed to generate Word document: {str(e)}")

    def generate_pdf_report(
        self,
        log_stats: Dict[str, Any],
        enriched_data: Dict[str, Dict[str, Any]],
        cti_stats: Dict[str, Any],
        file_path: str,
        tab_data: Optional[Dict[str, Any]] = None,
        embed_charts: bool = True
    ):
        if SimpleDocTemplate is None:
            raise Exception("reportlab is required. Install with: pip install reportlab")
        try:
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []

            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=22,
                spaceAfter=18,
                alignment=1,
                textColor=colors.HexColor("#203864"),
            )
            story.append(Paragraph("CTI Analysis Report", title_style))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
            story.append(Spacer(1, 12))

            story.append(Paragraph("Executive Summary", styles["Heading2"]))
            summary_rows = [["Metric", "Value"]] + self._summary_kv_rows(log_stats, cti_stats)
            tbl = Table(summary_rows)
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#404040")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F7F7F7")),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 12))

            # Charts (images)
            if embed_charts and plt is not None:
                chart_paths = self._render_charts_files(cti_stats, log_stats)
                for path in chart_paths.values():
                    try:
                        story.append(Spacer(1, 8))
                        story.append(RLImage(path, width=6.7 * inch, height=3.7 * inch))
                    except Exception:
                        pass
                story.append(Spacer(1, 16))

            # IP details
            story.append(Paragraph("IP Analysis Details", styles["Heading2"]))
            ip_rows = [["IP Address", "Threat Level", "Risk", "Abuse Conf.", "VT Rep."]]
            for ip, data in enriched_data.items():
                vt = data.get("virustotal", {}) or {}
                ab = data.get("abuseipdb", {}) or {}
                ip_rows.append([
                    ip,
                    str(data.get("overall_threat_level", "unknown")),
                    str(data.get("risk_score", 0)),
                    str(ab.get("abuse_confidence", "N/A")),
                    str(vt.get("reputation", "N/A")),
                ])
            ip_tbl = Table(ip_rows, repeatRows=1)
            ip_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#404040")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (2, 1), (-1, -1), "CENTER"),
            ]))
            story.append(ip_tbl)
            
            # Add AI Analysis sections
            if tab_data and 'ai_comprehensive_report' in tab_data:
                ai_report = tab_data['ai_comprehensive_report']
                if ai_report:
                    story.append(Spacer(1, 12))
                    story.append(Paragraph("AI Comprehensive Analysis", styles["Heading2"]))
                    story.append(Paragraph(ai_report, styles["Normal"]))
            
            if tab_data and 'ai_output' in tab_data:
                ai_output = tab_data['ai_output']
                if ai_output:
                    story.append(Spacer(1, 12))
                    story.append(Paragraph("AI Detailed Analysis", styles["Heading2"]))
                    story.append(Paragraph(ai_output, styles["Normal"]))
            
            if tab_data and 'statistics_data' in tab_data:
                stats_data = tab_data['statistics_data']
                ai_summary = stats_data.get('ai_summary', '')
                if ai_summary:
                    story.append(Spacer(1, 12))
                    story.append(Paragraph("Statistics Summary", styles["Heading2"]))
                    story.append(Paragraph(ai_summary, styles["Normal"]))
            
            if tab_data and 'map_data' in tab_data:
                map_data = tab_data['map_data']
                if map_data.get('markers'):
                    story.append(Spacer(1, 12))
                    story.append(Paragraph("Geographic Analysis", styles["Heading2"]))
                    story.append(Paragraph(f"Total IPs Mapped: {map_data.get('total_markers', 0)}", styles["Normal"]))
                    story.append(Paragraph("IP Geographic Distribution:", styles["Normal"]))
                    for marker in map_data.get('markers', []):
                        story.append(Paragraph(f"• {marker.get('ip', '')} - Threat: {marker.get('threat_level', '')} - Risk: {marker.get('risk_score', 0)}%", styles["Normal"]))
            
            doc.build(story)
            print(f"{Fore.GREEN}PDF report generated: {file_path}{Style.RESET_ALL}")
        except Exception as e:
            raise Exception(f"Failed to generate PDF report: {str(e)}")

    # ----------- Public: Excel -----------

    def generate_excel_report(
        self,
        log_stats: Dict[str, Any],
        enriched_data: Dict[str, Dict[str, Any]],
        cti_stats: Dict[str, Any],
        file_path: str,
        tab_data: Optional[Dict[str, Any]] = None
    ):
        if openpyxl is None:
            raise Exception("pandas/openpyxl are required for Excel export. pip install pandas openpyxl")
        try:
            wb = openpyxl.Workbook()

            # Summary sheet
            ws_sum = wb.active
            ws_sum.title = "Summary"
            summary = [["Metric", "Value"]] + self._summary_kv_rows(log_stats, cti_stats)
            for row in summary:
                ws_sum.append(row)
            self._style_header(ws_sum, 1)
            self._autosize(ws_sum)

            # Threat levels (tabular)
            ws_levels = wb.create_sheet("Threat Levels")
            ws_levels.append(["Level", "Count", "Percent"])
            total_ips = _safe_int(_safe_get(cti_stats, ["total_ips"], 0))
            for lvl in ["high", "medium", "low", "clean", "unknown"]:
                c = _safe_int(_safe_get(cti_stats, ["threat_levels", lvl], 0))
                ws_levels.append([lvl.capitalize(), c, f"{_pct(c, total_ips):.1f}%"])
            self._style_header(ws_levels, 1)
            self._autosize(ws_levels)

            # IP Details
            ws_det = wb.create_sheet("IP Details")
            headers = ["IP Address", "Threat Level", "Risk Score", "Abuse Confidence", "Abuse Risk Score", "VT Reputation"]
            ws_det.append(headers)
            for ip, data in enriched_data.items():
                vt = data.get("virustotal", {}) or {}
                ab = data.get("abuseipdb", {}) or {}
                ws_det.append([
                    ip,
                    str(data.get("overall_threat_level", "unknown")),
                    _safe_int(data.get("risk_score", 0)),
                    _safe_int(ab.get("abuse_confidence", 0)),
                    _safe_int(ab.get("risk_score", 0)),
                    vt.get("reputation", "N/A"),
                ])
            self._style_header(ws_det, 1)

            # Conditional formatting for Risk Score / Abuse Confidence
            try:
                max_row = ws_det.max_row
                # Color scale for Risk Score (column C)
                ws_det.conditional_formatting.add(f"C2:C{max_row}",
                    ColorScaleRule(start_type="min", start_color="63BE7B",  # green
                                   mid_type="percentile", mid_value=50, mid_color="FFEB84",  # yellow
                                   end_type="max", end_color="F8696B"))  # red
                # Flag high threat level rows
                for r in range(2, max_row + 1):
                    lvl_cell = ws_det.cell(row=r, column=2)
                    if str(lvl_cell.value).lower() == "high":
                        for c in range(1, ws_det.max_column + 1):
                            ws_det.cell(row=r, column=c).fill = PatternFill("solid", start_color="FFC7CE", end_color="FFC7CE")
            except Exception:
                pass
            self._autosize(ws_det)

            # Optional extra tabs
            if tab_data and "ai_output" in tab_data:
                ws_ai = wb.create_sheet("AI Analysis")
                for i, line in enumerate(str(tab_data.get("ai_output", "")).splitlines(), start=1):
                    ws_ai.cell(i, 1, line)
                ws_ai.column_dimensions["A"].width = 120

            if tab_data and "ai_comprehensive_report" in tab_data:
                ws_ai2 = wb.create_sheet("AI Comprehensive")
                for i, line in enumerate(str(tab_data.get("ai_comprehensive_report", "")).splitlines(), start=1):
                    ws_ai2.cell(i, 1, line)
                ws_ai2.column_dimensions["A"].width = 120

            wb.save(file_path)
            print(f"{Fore.GREEN}Excel report generated: {file_path}{Style.RESET_ALL}")
        except Exception as e:
            raise Exception(f"Failed to generate Excel report: {str(e)}")

    # ------------------------- Console Summary -------------------------

    def print_summary_table(self, cti_stats: Dict[str, Any]):
        """
        Advanced, colorized console summary:
        - Threat levels with mini bars
        - Risk distribution with mini bars
        - Totals and coverage
        """
        total_ips = _safe_int(_safe_get(cti_stats, ["total_ips"], 0))
        tl = {k: _safe_int(v) for k, v in (_safe_get(cti_stats, ["threat_levels"], {}) or {}).items()}
        rd = {k: _safe_int(v) for k, v in (_safe_get(cti_stats, ["risk_distribution"], {}) or {}).items()}
        src = _safe_get(cti_stats, ["source_availability"], {}) or {}

        print(f"\n{Fore.CYAN}=== THREAT INTELLIGENCE SUMMARY ==={Style.RESET_ALL}")
        th_rows = [["Threat Level", "Count", "Percent", "Bar"]]
        for label, color in [("high", Fore.RED), ("medium", Fore.YELLOW), ("low", Fore.BLUE), ("clean", Fore.GREEN), ("unknown", Fore.WHITE)]:
            cnt = _safe_int(tl.get(label, 0))
            bar = _bar(cnt, total_ips)
            th_rows.append([color + label.capitalize() + Style.RESET_ALL, cnt, f"{_pct(cnt, total_ips):.1f}%", bar])

        print(tabulate(th_rows, headers="firstrow", tablefmt="grid"))

        print(f"\n{Fore.CYAN}=== RISK DISTRIBUTION ==={Style.RESET_ALL}")
        rd_rows = [["Risk Bucket", "Count", "Percent", "Bar"]]
        order = [("high_risk", "High (70-100%)"), ("medium_risk", "Medium (30-69%)"),
                 ("low_risk", "Low (1-29%)"), ("no_risk", "No Risk (0%)")]
        for key, label in order:
            cnt = _safe_int(rd.get(key, 0))
            rd_rows.append([label, cnt, f"{_pct(cnt, total_ips):.1f}%", _bar(cnt, total_ips)])
        print(tabulate(rd_rows, headers="firstrow", tablefmt="grid"))

        print(f"\n{Fore.CYAN}=== CTI SOURCE COVERAGE ==={Style.RESET_ALL}")
        cov_rows = [["Source", "Resolved", "Coverage", "Bar"]]
        for source_name in ["virustotal", "abuseipdb", "greynoise"]:
            resolved = _safe_int(src.get(source_name, 0))
            cov_rows.append([source_name.capitalize(), resolved, f"{_pct(resolved, total_ips):.1f}%", _bar(resolved, total_ips)])
        print(tabulate(cov_rows, headers="firstrow", tablefmt="grid"))

    # ------------------------- Internal content builders -------------------------

    def _summary_kv_rows(self, log_stats: Dict[str, Any], cti_stats: Dict[str, Any]) -> List[Tuple[str, Any]]:
        # Use safe getters so missing keys don’t explode
        total_entries = _safe_int(_safe_get(log_stats, ["total_entries"], _safe_get(log_stats, ["total"], 0)))
        unique_ips = _safe_int(_safe_get(log_stats, ["unique_ips"], _safe_get(log_stats, ["total_count"], 0)))
        public_cnt = _safe_int(_safe_get(log_stats, ["public_count"], 0))
        private_cnt = _safe_int(_safe_get(log_stats, ["private_count"], 0))
        tl = {k: _safe_int(v) for k, v in (_safe_get(cti_stats, ["threat_levels"], {}) or {}).items()}
        return [
            ("Total Log Entries", total_entries),
            ("Unique IPs", unique_ips),
            ("Public IPs", public_cnt),
            ("Private IPs", private_cnt),
            ("High Threat IPs", tl.get("high", 0)),
            ("Medium Threat IPs", tl.get("medium", 0)),
            ("Low Threat IPs", tl.get("low", 0)),
            ("Clean IPs", tl.get("clean", 0)),
            ("Unknown Threat IPs", tl.get("unknown", 0)),
        ]

    def _generate_report_text(
        self, log_stats: Dict[str, Any], enriched: Dict[str, Dict[str, Any]], cti_stats: Dict[str, Any], 
        tab_data: Dict[str, Any] = None, map_image_path: Optional[str] = None, history_data: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        lines: List[str] = []
        lines += [
            "=" * 80,
            "LOG ANALYSIS & CYBER THREAT INTELLIGENCE REPORT",
            "=" * 80,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "EXECUTIVE SUMMARY",
            "-" * 40,
        ]
        for k, v in self._summary_kv_rows(log_stats, cti_stats):
            lines.append(f"{k}: {v}")
        lines.append("")

        lines += ["THREAT INTELLIGENCE SUMMARY", "-" * 40]
        tl = _safe_get(cti_stats, ["threat_levels"], {}) or {}
        lines.append(f"High threat IPs: {_safe_int(tl.get('high', 0))}")
        lines.append(f"Medium threat IPs: {_safe_int(tl.get('medium', 0))}")
        lines.append(f"Low threat IPs: {_safe_int(tl.get('low', 0))}")
        lines.append(f"Clean IPs: {_safe_int(tl.get('clean', 0))}")
        lines.append(f"Unknown threat level: {_safe_int(tl.get('unknown', 0))}")
        lines.append("")

        rd = _safe_get(cti_stats, ["risk_distribution"], {}) or {}
        lines += ["RISK DISTRIBUTION", "-" * 40]
        lines.append(f"High risk (70-100%): {_safe_int(rd.get('high_risk', 0))}")
        lines.append(f"Medium risk (30-69%): {_safe_int(rd.get('medium_risk', 0))}")
        lines.append(f"Low risk (1-29%): {_safe_int(rd.get('low_risk', 0))}")
        lines.append(f"No risk (0%): {_safe_int(rd.get('no_risk', 0))}")
        lines.append("")

        susp_ips = _safe_get(cti_stats, ["suspicious_ips"], []) or []
        if susp_ips:
            lines += ["SUSPICIOUS IP ADDRESSES (High Risk)", "-" * 40]
            for ip in susp_ips:
                ipd = enriched.get(ip, {}) or {}
                lines.append(f"IP: {ip}")
                lines.append(f"  Threat Level: {ipd.get('overall_threat_level', 'unknown')}")
                lines.append(f"  Risk Score: {_safe_int(ipd.get('risk_score', 0))}%")
                lines.append("")
        clean_ips = _safe_get(cti_stats, ["clean_ips"], []) or []
        if clean_ips:
            lines += ["CLEAN IP ADDRESSES (No Risk)", "-" * 40]
            for ip in clean_ips[:10]:
                lines.append(f"IP: {ip}")
            if len(clean_ips) > 10:
                lines.append(f"... and {len(clean_ips) - 10} more")
            lines.append("")

        lines += ["DETAILED IP ANALYSIS", "-" * 40]
        for ip, data in enriched.items():
            vt = data.get("virustotal", {}) or {}
            ab = data.get("abuseipdb", {}) or {}
            behavior = data.get("behavior", {}) or {}
            lines.append(f"IP Address: {ip}")
            lines.append(f"Overall Threat Level: {data.get('overall_threat_level', 'unknown')}")
            lines.append(f"Risk Score: {_safe_int(data.get('risk_score', 0))}%")
            if behavior:
                lines.append("  Behavior Analysis:")
                lines.append(f"    Behavior Threat: {behavior.get('threat_level', 'unknown')}")
                lines.append(f"    Behavior Score: {_safe_int(behavior.get('risk_score', 0))}%")
                indicators = behavior.get("indicators", []) or []
                if indicators:
                    lines.append(f"    Indicators: {', '.join(indicators)}")
                methods = behavior.get("methods", []) or []
                if methods:
                    lines.append(f"    Methods Seen: {', '.join(methods)}")
                statuses = behavior.get("statuses", {}) or {}
                if statuses:
                    status_s = ", ".join([f"{k}:{v}" for k, v in sorted(statuses.items())])
                    lines.append(f"    Statuses: {status_s}")
            if vt:
                lines.append("  VirusTotal Analysis:")
                lines.append(f"    Reputation Score: {vt.get('reputation', 'N/A')}")
                lines.append(f"    Threat Level: {vt.get('threat_level', 'unknown')}")
                st = vt.get("analysis_stats", {}) or {}
                lines.append(f"    Malicious: {_safe_int(st.get('malicious', 0))}")
                lines.append(f"    Suspicious: {_safe_int(st.get('suspicious', 0))}")
                lines.append(f"    Harmless: {_safe_int(st.get('harmless', 0))}")
            if ab:
                lines.append("  AbuseIPDB Analysis:")
                lines.append(f"    Abuse Confidence: {_safe_int(ab.get('abuse_confidence', 0))}%")
                lines.append(f"    Total Reports: {_safe_int(ab.get('total_reports', 0))}")
                lines.append(f"    Distinct Users: {_safe_int(ab.get('distinct_users', 0))}")
            lines.append("-" * 40)

        err = _safe_get(log_stats, ["error_codes"], {}) or {}
        if err:
            lines += ["HTTP ERROR CODES ANALYSIS", "-" * 40]
            for code, count in sorted(err.items()):
                lines.append(f"Status {code}: {_safe_int(count)} occurrences")
            lines.append("")

        ipfreq = _safe_get(log_stats, ["ip_frequency"], {}) or {}
        if ipfreq:
            lines += ["MOST FREQUENT IP ADDRESSES", "-" * 40]
            for ip, count in sorted(ipfreq.items(), key=lambda x: x[1], reverse=True)[:20]:
                lines.append(f"{ip}: {_safe_int(count)} occurrences")
            lines.append("")

        src = _safe_get(cti_stats, ["source_availability"], {}) or {}
        total_ips = _safe_int(_safe_get(cti_stats, ["total_ips"], 0))
        lines += ["CTI SOURCE AVAILABILITY", "-" * 40]
        lines.append(f"VirusTotal: {_safe_int(src.get('virustotal', 0))}/{total_ips} IPs")
        lines.append(f"AbuseIPDB: {_safe_int(src.get('abuseipdb', 0))}/{total_ips} IPs")
        if "greynoise" in src:
            lines.append(f"GreyNoise: {_safe_int(src.get('greynoise', 0))}/{total_ips} IPs")
        lines.append("Behavior Heuristics: Available for all IPs")
        lines.append("")

        # Recommendations
        lines += ["RECOMMENDATIONS", "-" * 40]
        high = _safe_int(tl.get("high", 0))
        med = _safe_int(tl.get("medium", 0))
        if high > 0:
            lines.append(f"• {high} IP addresses are classified as HIGH RISK")
            lines.append("  - Immediately block on WAF/Firewall where applicable")
            lines.append("  - Investigate related events and correlate across logs/SIEM")
            lines.append("  - Add detection rules for repeated behaviors")
            lines.append("")
        if med > 0:
            lines.append(f"• {med} IP addresses are classified as MEDIUM RISK")
            lines.append("  - Monitor closely; throttle or geofence if feasible")
            lines.append("  - Tighten rate limits and anomaly alerts")
            lines.append("")
        if high == 0 and med == 0:
            lines.append("• No high/medium risk IPs detected")
            lines.append("  - Maintain current monitoring and review on schedule")
            lines.append("")

        # Add AI Analysis section
        if tab_data and 'ai_comprehensive_report' in tab_data:
            ai_report = tab_data['ai_comprehensive_report']
            if ai_report:
                lines += ["AI COMPREHENSIVE ANALYSIS", "-" * 40]
                lines.append(ai_report)
                lines.append("")
        
        # Add AI Output section
        if tab_data and 'ai_output' in tab_data:
            ai_output = tab_data['ai_output']
            if ai_output:
                lines += ["AI DETAILED ANALYSIS", "-" * 40]
                lines.append(ai_output)
                lines.append("")
        
        # Add Statistics Summary
        if tab_data and 'statistics_data' in tab_data:
            stats_data = tab_data['statistics_data']
            ai_summary = stats_data.get('ai_summary', '')
            if ai_summary:
                lines += ["STATISTICS SUMMARY", "-" * 40]
                lines.append(ai_summary)
                lines.append("")
        
        # Add Map Analysis
        if tab_data and 'map_data' in tab_data:
            map_data = tab_data['map_data']
            if map_data.get('markers'):
                lines += ["GEOGRAPHIC ANALYSIS", "-" * 40]
                lines.append(f"Total IPs Mapped: {map_data.get('total_markers', 0)}")
                lines.append("")
                lines.append("IP Geographic Distribution:")
                for marker in map_data.get('markers', []):
                    lines.append(f"  {marker.get('ip', '')} - Threat: {marker.get('threat_level', '')} - Risk: {marker.get('risk_score', 0)}%")
                lines.append("")
        
        # Add map information if available
        if map_image_path and os.path.exists(map_image_path):
            lines += ["", "GEOGRAPHIC MAP", "-" * 40]
            lines.append(f"Map image saved at: {map_image_path}")
            lines.append("The map shows the geographical distribution of analyzed IP addresses.")
            lines.append("")
        
        # Add history data if available
        if history_data:
            lines += ["", "ANALYSIS HISTORY", "-" * 40]
            lines.append(f"Total analysis sessions: {len(history_data)}")
            lines.append("")
            for i, session in enumerate(history_data, 1):
                lines.append(f"Session {i}:")
                lines.append(f"  Date: {session.get('date', 'Unknown')}")
                lines.append(f"  File: {session.get('filename', 'Unknown')}")
                lines.append(f"  IPs Analyzed: {session.get('ip_count', 0)}")
                lines.append(f"  Threats Found: {session.get('threat_count', 0)}")
                if session.get('notes'):
                    lines.append(f"  Notes: {session.get('notes')}")
                lines.append("")
        
        lines.append("=" * 80)
        return "\n".join(lines)

    def _generate_markdown_content(
        self,
        log_stats: Dict[str, Any],
        enriched: Dict[str, Dict[str, Any]],
        cti_stats: Dict[str, Any],
        tab_data: Optional[Dict[str, Any]] = None,
        chart_b64: Optional[Dict[str, str]] = None
    ) -> str:
        out: List[str] = []
        out += [
            "# CTI Analysis Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Executive Summary",
            "",
        ]
        for k, v in self._summary_kv_rows(log_stats, cti_stats):
            out.append(f"- **{k}:** {v}")
        out.append("")

        # Optional charts inline
        if chart_b64:
            for title, b64 in chart_b64.items():
                out.append(f"### {title}")
                out.append(f"![{title}](data:image/png;base64,{b64})")
                out.append("")

        out += [
            "## Threat Intelligence Summary",
            "",
        ]
        tl = _safe_get(cti_stats, ["threat_levels"], {}) or {}
        out += [
            f"- **High Threat IPs:** {_safe_int(tl.get('high', 0))}",
            f"- **Medium Threat IPs:** {_safe_int(tl.get('medium', 0))}",
            f"- **Low Threat IPs:** {_safe_int(tl.get('low', 0))}",
            f"- **Clean IPs:** {_safe_int(tl.get('clean', 0))}",
            f"- **Unknown Threat IPs:** {_safe_int(tl.get('unknown', 0))}",
            "",
        ]

        out += [
            "## IP Analysis Details",
            "",
            "| IP Address | Threat Level | Risk Score | Abuse Confidence | VT Reputation |",
            "|------------|--------------|------------|------------------|---------------|",
        ]
        for ip, data in enriched.items():
            vt = data.get("virustotal", {}) or {}
            ab = data.get("abuseipdb", {}) or {}
            out.append(
                f"| {ip} | {data.get('overall_threat_level', 'unknown')} | "
                f"{_safe_int(data.get('risk_score', 0))} | {_safe_int(ab.get('abuse_confidence', 0))} | "
                f"{vt.get('reputation', 'N/A')} |"
            )
        out.append("")

        # Extra sections from tab_data
        if tab_data and tab_data.get("statistics_data", {}).get("ai_summary"):
            out += ["## AI Summary", "", tab_data["statistics_data"]["ai_summary"], ""]
        if tab_data and tab_data.get("ai_output"):
            out += ["## AI Analysis Results", "", "```", str(tab_data["ai_output"]), "```", ""]
        if tab_data and tab_data.get("ai_comprehensive_report"):
            out += ["## AI Comprehensive Analysis Report", "", str(tab_data["ai_comprehensive_report"]), ""]

        return "\n".join(out)

    def _generate_html_content(
        self,
        log_stats: Dict[str, Any],
        enriched: Dict[str, Dict[str, Any]],
        cti_stats: Dict[str, Any],
        tab_data: Optional[Dict[str, Any]],
        chart_b64: Optional[Dict[str, str]],
        map_image_path: Optional[str] = None,
        history_data: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        # Simple, clean, single-file HTML with embedded images
        def row(k: str, v: Any) -> str:
            return f"<tr><td>{k}</td><td>{v}</td></tr>"

        summary_rows = "\n".join([row(k, v) for k, v in self._summary_kv_rows(log_stats, cti_stats)])
        charts_html = ""
        if chart_b64:
            for title, b64 in chart_b64.items():
                charts_html += f"<h3>{title}</h3><img alt='{title}' src='data:image/png;base64,{b64}' style='max-width:100%;height:auto;margin:8px 0;'/>"

        ips_html_rows = []
        for ip, data in enriched.items():
            vt = data.get("virustotal", {}) or {}
            ab = data.get("abuseipdb", {}) or {}
            ips_html_rows.append(
                "<tr>" +
                f"<td>{ip}</td>" +
                f"<td>{data.get('overall_threat_level', 'unknown')}</td>" +
                f"<td>{_safe_int(data.get('risk_score', 0))}</td>" +
                f"<td>{_safe_int(ab.get('abuse_confidence', 0))}</td>" +
                f"<td>{vt.get('reputation', 'N/A')}</td>" +
                "</tr>"
            )
        ips_html = "\n".join(ips_html_rows)

        ai_blocks = ""
        if tab_data and tab_data.get("statistics_data", {}).get("ai_summary"):
            ai_blocks += f"<h2>AI Summary</h2><pre>{tab_data['statistics_data']['ai_summary']}</pre>"
        if tab_data and tab_data.get("ai_output"):
            ai_blocks += f"<h2>AI Analysis Results</h2><pre>{tab_data['ai_output']}</pre>"
        if tab_data and tab_data.get("ai_comprehensive_report"):
            ai_blocks += f"<h2>AI Comprehensive Analysis Report</h2><pre>{tab_data['ai_comprehensive_report']}</pre>"

        # Map section
        map_section = ""
        if map_image_path and os.path.exists(map_image_path):
            try:
                with open(map_image_path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    map_section = f"""
  <div class="card">
    <h2>Geographic Map</h2>
    <p>The map shows the geographical distribution of analyzed IP addresses.</p>
    <img src="data:image/png;base64,{img_data}" alt="Geographic Map" style="max-width: 100%; height: auto; border: 1px solid #2b3137; border-radius: 4px;">
  </div>"""
            except Exception:
                map_section = f"""
  <div class="card">
    <h2>Geographic Map</h2>
    <p>Map image saved at: {map_image_path}</p>
    <p>The map shows the geographical distribution of analyzed IP addresses.</p>
  </div>"""

        # History section
        history_section = ""
        if history_data:
            history_rows = ""
            for i, session in enumerate(history_data, 1):
                history_rows += f"""
      <tr>
        <td>{i}</td>
        <td>{session.get('date', 'Unknown')}</td>
        <td>{session.get('filename', 'Unknown')}</td>
        <td>{session.get('ip_count', 0)}</td>
        <td>{session.get('threat_count', 0)}</td>
        <td>{session.get('notes', 'N/A')}</td>
      </tr>"""
            
            history_section = f"""
  <div class="card">
    <h2>Analysis History</h2>
    <p>Total analysis sessions: {len(history_data)}</p>
    <table>
      <thead>
        <tr><th>Session</th><th>Date</th><th>File</th><th>IPs Analyzed</th><th>Threats Found</th><th>Notes</th></tr>
      </thead>
      <tbody>
        {history_rows}
      </tbody>
    </table>
  </div>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>CTI Analysis Report</title>
<style>
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, "Helvetica Neue", Arial, sans-serif; background:#0e1113; color:#e6e6e6; padding:24px; }}
  h1,h2,h3 {{ color:#f5a623; margin: 0.4em 0; }}
  .card {{ background:#151a1f; border-radius:12px; padding:16px; margin:16px 0; box-shadow:0 0 0 1px #20252b inset; }}
  table {{ width:100%; border-collapse: collapse; font-size:14px; }}
  th, td {{ border-bottom:1px solid #2b3137; padding:8px 10px; text-align:left; }}
  th {{ background:#20252b; color:#f0f0f0; }}
  .muted {{ opacity:0.85; }}
</style>
</head>
<body>
  <h1>CTI Analysis Report</h1>
  <div class="muted">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>

  <div class="card">
    <h2>Executive Summary</h2>
    <table>
      <thead><tr><th>Metric</th><th>Value</th></tr></thead>
      <tbody>
        {summary_rows}
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>Visual Overview</h2>
    {charts_html if charts_html else "<div class='muted'>Charts unavailable (matplotlib not installed).</div>"}
  </div>

  <div class="card">
    <h2>IP Analysis Details</h2>
    <table>
      <thead><tr><th>IP Address</th><th>Threat Level</th><th>Risk</th><th>Abuse Conf.</th><th>VT Rep.</th></tr></thead>
      <tbody>
        {ips_html}
      </tbody>
    </table>
  </div>

  <div class="card">
    {ai_blocks}
  </div>
  
  {map_section}
  {history_section}
</body>
</html>"""

    # ------------------------- Chart rendering -------------------------

    def _render_charts_b64(self, log_stats: Dict[str, Any], cti_stats: Dict[str, Any]) -> Dict[str, str]:
        """Return dict of chart_name -> base64 PNG strings."""
        if plt is None:
            return {}
        charts: Dict[str, str] = {}

        # 1) Threat Level Distribution (bar)
        tl = _safe_get(cti_stats, ["threat_levels"], {}) or {}
        labels = ["High", "Medium", "Low", "Clean", "Unknown"]
        values = [_safe_int(tl.get(k.lower(), 0)) for k in labels]
        fig1 = plt.figure(figsize=(7, 3.5))
        plt.title("Threat Level Distribution")
        plt.bar(labels, values)
        plt.xlabel("Level")
        plt.ylabel("Count")
        charts["Threat Level Distribution"] = _as_base64_png(fig1)

        # 2) Risk Distribution (bar)
        rd = _safe_get(cti_stats, ["risk_distribution"], {}) or {}
        labels2 = ["High (70-100)", "Medium (30-69)", "Low (1-29)", "No Risk (0)"]
        values2 = [
            _safe_int(rd.get("high_risk", 0)),
            _safe_int(rd.get("medium_risk", 0)),
            _safe_int(rd.get("low_risk", 0)),
            _safe_int(rd.get("no_risk", 0)),
        ]
        fig2 = plt.figure(figsize=(7, 3.5))
        plt.title("Risk Distribution")
        plt.bar(labels2, values2)
        plt.xticks(rotation=15, ha="right")
        plt.xlabel("Bucket")
        plt.ylabel("Count")
        charts["Risk Distribution"] = _as_base64_png(fig2)

        # 3) HTTP Status Overview (if available)
        codes = _safe_get(log_stats, ["error_codes"], {}) or {}
        if codes:
            labels3 = list(map(str, sorted(codes.keys())))
            values3 = [_safe_int(codes[k]) for k in sorted(codes.keys())]
            fig3 = plt.figure(figsize=(7, 3.5))
            plt.title("HTTP Error Codes")
            plt.bar(labels3, values3)
            plt.xlabel("Status Code")
            plt.ylabel("Count")
            charts["HTTP Error Codes"] = _as_base64_png(fig3)

        return charts

    def _render_charts_files(self, cti_stats: Dict[str, Any], log_stats: Dict[str, Any]) -> Dict[str, str]:
        """Render charts to PNG files in output_dir; return dict of name->path."""
        if plt is None:
            return {}
        paths: Dict[str, str] = {}

        def save_fig(fig, name: str) -> str:
            path = os.path.join(self.output_dir, f"{name}_{_now_stamp()}.png")
            fig.savefig(path, bbox_inches="tight")
            plt.close(fig)
            return path

        tl = _safe_get(cti_stats, ["threat_levels"], {}) or {}
        labels = ["High", "Medium", "Low", "Clean", "Unknown"]
        values = [_safe_int(tl.get(k.lower(), 0)) for k in labels]
        fig1 = plt.figure(figsize=(7, 3.5))
        plt.title("Threat Level Distribution")
        plt.bar(labels, values)
        plt.xlabel("Level")
        plt.ylabel("Count")
        paths["threat_levels"] = save_fig(fig1, "threat_levels")

        rd = _safe_get(cti_stats, ["risk_distribution"], {}) or {}
        labels2 = ["High (70-100)", "Medium (30-69)", "Low (1-29)", "No Risk (0)"]
        values2 = [
            _safe_int(rd.get("high_risk", 0)),
            _safe_int(rd.get("medium_risk", 0)),
            _safe_int(rd.get("low_risk", 0)),
            _safe_int(rd.get("no_risk", 0)),
        ]
        fig2 = plt.figure(figsize=(7, 3.5))
        plt.title("Risk Distribution")
        plt.bar(labels2, values2)
        plt.xticks(rotation=15, ha="right")
        plt.xlabel("Bucket")
        plt.ylabel("Count")
        paths["risk_distribution"] = save_fig(fig2, "risk_distribution")

        codes = _safe_get(log_stats, ["error_codes"], {}) or {}
        if codes:
            labels3 = list(map(str, sorted(codes.keys())))
            values3 = [_safe_int(codes[k]) for k in sorted(codes.keys())]
            fig3 = plt.figure(figsize=(7, 3.5))
            plt.title("HTTP Error Codes")
            plt.bar(labels3, values3)
            plt.xlabel("Status Code")
            plt.ylabel("Count")
            paths["http_errors"] = save_fig(fig3, "http_errors")

        return paths

    # ------------------------- Styling helpers (Excel) -------------------------

    def _style_header(self, ws, header_row_idx: int = 1):
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        for cell in ws[header_row_idx]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

    def _autosize(self, ws, max_width: int = 60):
        for column_cells in ws.columns:
            max_len = 0
            col_letter = column_cells[0].column_letter
            for c in column_cells:
                try:
                    max_len = max(max_len, len(str(c.value)))
                except Exception:
                    pass
            ws.column_dimensions[col_letter].width = min(max_len + 2, max_width)
