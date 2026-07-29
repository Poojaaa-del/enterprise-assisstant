# backend/agents/report.py
"""
ReportAgent
Structures AI answers with grounded citations into a human-readable Executive Summary
and optionally renders it as a downloadable PDF via reportlab.
"""
from typing import List
from io import BytesIO
from datetime import datetime


class ReportAgent:
    """
    Formats retrieved context + AI answer into:
      1. A structured markdown-compatible report dict
      2. A PDF byte stream (optional)
    """

    def format(self, query: str, answer: str, citations: List[dict], confidence: int) -> dict:
        """
        Returns a structured report dictionary ready for JSON serialization.
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        return {
            "title":            "Enterprise Intelligence Report",
            "timestamp":        timestamp,
            "query":            query,
            "executive_summary": answer,
            "confidence_score": confidence,
            "citations":        citations,
            "citation_count":   len(citations),
        }

    def to_pdf(self, query: str, answer: str, citations: List[dict], confidence: int) -> bytes:
        """
        Generates a PDF document and returns it as raw bytes.
        Uses reportlab for zero-dependency PDF generation.
        """
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )

        buffer = BytesIO()
        doc    = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()

        # ── Custom styles ────────────────────────────────────────────────────
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Title"],
            fontSize=18,
            textColor=colors.HexColor("#1a1a2e"),
            spaceAfter=6,
        )
        header_style = ParagraphStyle(
            "Header",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#16213e"),
            spaceBefore=14,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#2d2d2d"),
        )
        meta_style = ParagraphStyle(
            "Meta",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#555555"),
            spaceAfter=2,
        )

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        elements  = []

        # ── Title block ──────────────────────────────────────────────────────
        elements.append(Paragraph("GuardCore Enterprise Intelligence Report", title_style))
        elements.append(Paragraph(f"Generated: {timestamp}", meta_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f3460"), spaceAfter=10))

        # ── Query ────────────────────────────────────────────────────────────
        elements.append(Paragraph("Query", header_style))
        elements.append(Paragraph(query, body_style))
        elements.append(Spacer(1, 8))

        # ── Confidence ───────────────────────────────────────────────────────
        confidence_color = (
            "#27ae60" if confidence >= 70
            else "#e67e22" if confidence >= 40
            else "#c0392b"
        )
        elements.append(
            Paragraph(
                f'<font color="{confidence_color}">Confidence Score: {confidence}%</font>',
                meta_style,
            )
        )
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=6))

        # ── Executive Summary ────────────────────────────────────────────────
        elements.append(Paragraph("Executive Summary", header_style))
        # Escape HTML entities in the answer
        safe_answer = answer.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        for para in safe_answer.split("\n\n"):
            if para.strip():
                elements.append(Paragraph(para.strip(), body_style))
                elements.append(Spacer(1, 4))

        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceBefore=10, spaceAfter=6))

        # ── Citations table ──────────────────────────────────────────────────
        if citations:
            elements.append(Paragraph("Source Citations", header_style))
            table_data = [["#", "Filename", "Page / Row", "Confidence", "Snippet"]]
            for i, cit in enumerate(citations, 1):
                snippet = cit.get("snippet", "")[:80] + "…" if len(cit.get("snippet", "")) > 80 else cit.get("snippet", "")
                table_data.append([
                    str(i),
                    cit.get("filename", "—"),
                    str(cit.get("page", "—")),
                    f"{cit.get('score', 0)}%",
                    snippet,
                ])
            tbl = Table(table_data, colWidths=[0.5*cm, 4*cm, 2*cm, 2.5*cm, None])
            tbl.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#0f3460")),
                ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
                ("FONTSIZE",    (0, 0), (-1, 0), 9),
                ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f4f6fb"), colors.white]),
                ("FONTSIZE",    (0, 1), (-1, -1), 8),
                ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                ("VALIGN",      (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING",(0, 0), (-1, -1), 4),
            ]))
            elements.append(tbl)

        # ── Footer ───────────────────────────────────────────────────────────
        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        elements.append(
            Paragraph(
                "This report was auto-generated by the GuardCore Enterprise AI. "
                "Always verify outputs against authoritative sources before taking action.",
                meta_style,
            )
        )

        doc.build(elements)
        return buffer.getvalue()
