import json
import logging
import os
from flask import Blueprint, request, jsonify, session, current_app

from services import company_service, gemini_service

logger = logging.getLogger(__name__)
company_bp = Blueprint("company", __name__)


def _load_report(report_id: str) -> dict | None:
    path = os.path.join(current_app.root_path, "reports", f"{report_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@company_bp.route("/company-analyze", methods=["POST"])
def analyze():
    """AJAX endpoint: analyze resume against a specific company's hiring bar."""
    report_id = session.get("report_id")
    if not report_id:
        return jsonify({"error": "No active analysis session."}), 400

    report = _load_report(report_id)
    if report is None:
        return jsonify({"error": "Report expired. Please run a new analysis."}), 400

    company_key = request.json.get("company", "") if request.is_json else request.form.get("company", "")
    if company_key not in company_service.COMPANIES:
        return jsonify({"error": f"Unknown company: {company_key!r}"}), 400

    api_key = current_app.config.get("GEMINI_API_KEY", "")
    if not api_key:
        return jsonify({"error": "Gemini API key not configured."}), 503

    try:
        gemini_service.configure(api_key)
        result = company_service.analyze_for_company(
            company_key,
            resume_text=report.get("resume_text", ""),
            jd_text=report.get("jd_text", ""),
        )
        return jsonify(result)
    except Exception as exc:
        logger.error("Company analysis error: %s", exc)
        return jsonify({"error": str(exc)}), 500
