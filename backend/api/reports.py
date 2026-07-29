# backend/api/reports.py
"""
Reports API
POST /api/v1/reports/export-pdf — Generates and streams a PDF report as a file download.
"""

from io import BytesIO
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from agents import ReportAgent
from api.auth import get_current_user

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])

_report_agent = None


def _get_report_agent() -> ReportAgent:
    global _report_agent
    if _report_agent is None:
        _report_agent = ReportAgent()
    return _report_agent


class CitationItem(BaseModel):
    # Allows extra attributes (e.g. overlap_percent) without throwing 422 validation errors
    model_config = ConfigDict(extra="allow")

    filename: Optional[str] = "Unknown"
    page: Optional[Any] = "—"  # Accepts int, str, or None
    snippet: Optional[str] = ""
    score: Optional[float] = 0.0


class ExportPDFRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    query: str = Field(default="Enterprise Query")
    answer: str = Field(default="")
    citations: Optional[List[Any]] = Field(default_factory=list)
    confidence: Optional[int] = Field(default=0)


@router.post("/export-pdf")
async def export_pdf_report(
    payload: ExportPDFRequest,
    current_user=Depends(get_current_user),
):
    """
    Accepts a query, AI answer, citations, and confidence score,
    generates a professionally styled PDF report, and streams it as a file download.
    """
    try:
        agent = _get_report_agent()

        # Safely convert citations regardless of whether they arrive as dicts or models
        citations_dicts = []
        for item in payload.citations:
            if isinstance(item, dict):
                citations_dicts.append(item)
            elif hasattr(item, "model_dump"):
                citations_dicts.append(item.model_dump())
            elif hasattr(item, "dict"):
                citations_dicts.append(item.dict())
            else:
                citations_dicts.append({"snippet": str(item)})

        pdf_bytes = agent.to_pdf(
            query=payload.query,
            answer=payload.answer,
            citations=citations_dicts,
            confidence=payload.confidence or 0,
        )

        # Build a safe filename from the query
        safe_name = "".join(
            c if c.isalnum() or c in (" ", "_", "-") else "_"
            for c in payload.query[:40]
        ).strip().replace(" ", "_")
        filename = f"guardcore_report_{safe_name or 'summary'}.pdf"

        return StreamingResponse(
            content=BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )

    except Exception as exc:
        print(f"[ERROR] [ReportExport] PDF generation failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {str(exc)}",
        )