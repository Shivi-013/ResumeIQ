import json
import logging
import os
from flask import Blueprint, session, redirect, url_for, flash, current_app, Response

from services.report_generator import generate_pdf

logger = logging.getLogger(__name__)
report_bp = Blueprint("report", __name__)


def _load_report(report_id: str) -> dict | None:
    path = os.path.join(current_app.root_path, "reports", f"{report_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@report_bp.route("/report/download")
def download():
    report_id = session.get("report_id")
    if not report_id:
        flash("No analysis found. Please run an analysis first.", "info")
        return redirect(url_for("analyzer.analyze"))

    report = _load_report(report_id)
    if report is None:
        flash("Report expired or not found. Please run a new analysis.", "error")
        return redirect(url_for("analyzer.analyze"))

    try:
        pdf_bytes = generate_pdf(report)
    except Exception as exc:
        logger.error("PDF generation error: %s", exc)
        flash("Could not generate PDF. Please try again.", "error")
        return redirect(url_for("analyzer.results"))

    filename = report.get("filename", "resume").replace(".pdf", "")
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="ResumeIQ_Report_{filename}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
