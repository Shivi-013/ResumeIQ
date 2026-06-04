import os
import uuid
import logging
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, current_app,
)
from werkzeug.utils import secure_filename

from utils.validators import validate_pdf, validate_jd
from services.resume_parser import extract_text
from services import gemini_service, semantic_service
from services.job_analyzer import compute_keyword_coverage

logger = logging.getLogger(__name__)
compare_bp = Blueprint("compare", __name__)


@compare_bp.route("/compare", methods=["GET"])
def compare():
    return render_template("compare.html")


@compare_bp.route("/compare", methods=["POST"])
def compare_post():
    # ── Validate both files ──
    file_a = request.files.get("resume_a")
    file_b = request.files.get("resume_b")
    jd_text = request.form.get("job_description", "")

    valid_a, err_a = validate_pdf(file_a)
    valid_b, err_b = validate_pdf(file_b)
    valid_jd, err_jd = validate_jd(jd_text)

    if not valid_a:
        flash(f"Resume A: {err_a}", "error")
        return redirect(url_for("compare.compare"))
    if not valid_b:
        flash(f"Resume B: {err_b}", "error")
        return redirect(url_for("compare.compare"))
    if not valid_jd:
        flash(err_jd, "error")
        return redirect(url_for("compare.compare"))

    # ── Extract text for both resumes ──
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    texts = {}
    names = {}
    for key, file in [("a", file_a), ("b", file_b)]:
        fname = secure_filename(file.filename)
        path = os.path.join(upload_folder, f"{uuid.uuid4().hex}_{fname}")
        try:
            file.save(path)
            texts[key] = extract_text(path)
            names[key] = fname
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("compare.compare"))
        finally:
            if os.path.exists(path):
                os.remove(path)

    if not texts["a"].strip() or not texts["b"].strip():
        flash("Could not extract text from one or both PDFs.", "error")
        return redirect(url_for("compare.compare"))

    # ── Run lightweight Gemini analysis for each ──
    api_key = current_app.config.get("GEMINI_API_KEY", "")
    results = {}
    for key in ("a", "b"):
        try:
            if api_key:
                gemini_service.configure(api_key)
                results[key] = gemini_service.analyze_compare(texts[key], jd_text)
            else:
                results[key] = _local_fallback(texts[key], jd_text)
        except Exception as exc:
            logger.warning("Gemini compare failed for %s: %s", key, exc)
            results[key] = _local_fallback(texts[key], jd_text)

    # ── Semantic similarity for each ──
    sem = {}
    for key in ("a", "b"):
        sem[key] = semantic_service.compute_similarity(texts[key], jd_text)

    # ── Keyword coverage ──
    req_skills = results["a"].get("required_skills", []) or results["b"].get("required_skills", [])
    coverage = {
        "a": compute_keyword_coverage(texts["a"], req_skills),
        "b": compute_keyword_coverage(texts["b"], req_skills),
    }

    # ── Build comparison summary ──
    def score_delta(field):
        return results["b"].get(field, 0) - results["a"].get(field, 0)

    comparison = {
        "results_a": results["a"],
        "results_b": results["b"],
        "name_a": names["a"],
        "name_b": names["b"],
        "sem_a": sem["a"],
        "sem_b": sem["b"],
        "coverage_a": coverage["a"],
        "coverage_b": coverage["b"],
        "delta_overall":    score_delta("overall_score"),
        "delta_ats":        score_delta("ats_score"),
        "delta_skills":     score_delta("skills_score"),
        "delta_experience": score_delta("experience_score"),
        "delta_education":  score_delta("education_score"),
        "winner": "B" if results["b"].get("overall_score", 0) >= results["a"].get("overall_score", 0) else "A",
        "fallback": not bool(api_key),
    }

    return render_template("compare.html", comparison=comparison)


# ── Local fallback (no Gemini) ────────────────────────────────────────────────
def _local_fallback(resume_text: str, jd_text: str) -> dict:
    from services.job_analyzer import extract_keywords, calculate_keyword_overlap
    kws = extract_keywords(jd_text)
    overlap = calculate_keyword_overlap(resume_text, kws)
    s = overlap["skills_score"]
    return {
        "overall_score":    max(10, s - 5),
        "ats_score":        max(10, s - 8),
        "skills_score":     s,
        "experience_score": max(10, s - 5),
        "education_score":  max(10, s - 5),
        "required_skills":  overlap["found_skills"] + overlap["missing_skills"],
        "found_skills":     overlap["found_skills"],
        "missing_skills":   overlap["missing_skills"],
        "sections": {
            "skills":     {"score": s, "feedback": "Based on keyword overlap."},
            "experience": {"score": s, "feedback": "Based on keyword overlap."},
            "education":  {"score": s, "feedback": "Based on keyword overlap."},
            "projects":   {"score": s, "feedback": "Based on keyword overlap."},
        },
        "strengths": ["Keyword overlap found."],
        "weaknesses": [f"{len(overlap['missing_skills'])} keywords missing."],
        "recommendation": "Moderate Match",
        "recommendation_reason": f"~{s}% keyword match.",
    }
