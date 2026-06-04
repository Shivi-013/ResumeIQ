import datetime
import json
import logging
import os
import uuid
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
)
from werkzeug.utils import secure_filename

from utils.validators import validate_pdf, validate_jd
from services.resume_parser import extract_text
from services import job_analyzer, gemini_service, semantic_service
from services.job_analyzer import compute_keyword_coverage

logger = logging.getLogger(__name__)
analyzer_bp = Blueprint("analyzer", __name__)


# ── Report file helpers ────────────────────────────────────────────────────────

def _report_path(report_id: str) -> str:
    return os.path.join(current_app.root_path, "reports", f"{report_id}.json")


def _save_report(data: dict) -> str:
    report_id = uuid.uuid4().hex
    os.makedirs(os.path.join(current_app.root_path, "reports"), exist_ok=True)
    with open(_report_path(report_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return report_id


def _load_report(report_id: str) -> dict | None:
    path = _report_path(report_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _cleanup_old_reports(root: str, max_age_hours: int = 2) -> None:
    """Remove report JSON files older than max_age_hours."""
    folder = os.path.join(root, "reports")
    cutoff = datetime.datetime.now().timestamp() - max_age_hours * 3600
    try:
        for name in os.listdir(folder):
            if not name.endswith(".json"):
                continue
            path = os.path.join(folder, name)
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
    except Exception as exc:
        logger.debug("Report cleanup skipped: %s", exc)


# ── Routes ────────────────────────────────────────────────────────────────────

@analyzer_bp.route("/analyze", methods=["GET"])
def analyze():
    return render_template("analyzer.html")


@analyzer_bp.route("/analyze", methods=["POST"])
def analyze_post():
    _cleanup_old_reports(current_app.root_path)

    # ── Validate ──
    resume_file = request.files.get("resume")
    valid, error = validate_pdf(resume_file)
    if not valid:
        flash(error, "error")
        return redirect(url_for("analyzer.analyze"))

    jd_text = request.form.get("job_description", "")
    valid, error = validate_jd(jd_text)
    if not valid:
        flash(error, "error")
        return redirect(url_for("analyzer.analyze"))

    # ── Extract PDF text ──
    filename = secure_filename(resume_file.filename)
    tmp_path = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        f"{uuid.uuid4().hex}_{filename}",
    )
    try:
        resume_file.save(tmp_path)
        resume_text = extract_text(tmp_path)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("analyzer.analyze"))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    if not resume_text.strip():
        flash("Could not extract text from the PDF. Use a text-based (non-scanned) PDF.", "error")
        return redirect(url_for("analyzer.analyze"))

    jd_text = jd_text.strip()
    logger.info("Resume parsed (%d chars), JD (%d chars)", len(resume_text), len(jd_text))

    # ── Gemini analysis ──
    api_key = current_app.config.get("GEMINI_API_KEY", "")
    fallback_used = False
    analysis = None

    if api_key:
        try:
            gemini_service.configure(api_key)
            analysis = gemini_service.analyze(resume_text, jd_text)
        except Exception as exc:
            logger.warning("Gemini failed, using fallback: %s", exc)
            fallback_used = True
    else:
        logger.warning("GEMINI_API_KEY not set — using fallback scoring.")
        fallback_used = True

    if fallback_used or analysis is None:
        analysis = _build_fallback(resume_text, jd_text)
        analysis["_fallback"] = True

    # ── Semantic similarity ──
    semantic_score = semantic_service.compute_similarity(resume_text, jd_text)

    # ── Keyword coverage ──
    required_skills = analysis.get("required_skills", [])
    keyword_coverage = compute_keyword_coverage(resume_text, required_skills)

    # ── Persist report to file (avoids cookie size limits) ──
    report = {
        "analysis": analysis,
        "filename": filename,
        "resume_text": resume_text[:8000],
        "jd_text": jd_text[:4000],
        "semantic_score": semantic_score,
        "keyword_coverage": keyword_coverage,
    }
    report_id = _save_report(report)
    session["report_id"] = report_id

    return redirect(url_for("analyzer.results"))


@analyzer_bp.route("/results")
def results():
    report_id = session.get("report_id")
    if not report_id:
        flash("No analysis found. Please upload your resume and job description first.", "info")
        return redirect(url_for("analyzer.analyze"))

    report = _load_report(report_id)
    if report is None:
        flash("Report expired. Please run a new analysis.", "error")
        return redirect(url_for("analyzer.analyze"))

    return render_template(
        "results.html",
        analysis=report["analysis"],
        filename=report.get("filename", ""),
        semantic_score=report.get("semantic_score"),
        keyword_coverage=report.get("keyword_coverage", []),
    )


# ── Fallback scoring (no Gemini) ──────────────────────────────────────────────

def _build_fallback(resume_text: str, jd_text: str) -> dict:
    kws = job_analyzer.extract_keywords(jd_text)
    overlap = job_analyzer.calculate_keyword_overlap(resume_text, kws)

    s = overlap["skills_score"]
    overall = max(10, s - 5)
    found = overlap["found_skills"]
    missing = overlap["missing_skills"]

    rec = ("Strong Match" if overall >= 70
           else "Moderate Match" if overall >= 45
           else "Weak Match")

    return {
        "overall_score":    overall,
        "ats_score":        max(10, overall - 8),
        "skills_score":     s,
        "experience_score": overall,
        "education_score":  overall,
        "required_skills":  (found + missing)[:30],
        "found_skills":     found[:30],
        "missing_skills":   missing[:30],
        "sections": {
            "skills":     {"score": s,       "feedback": "Based on keyword overlap analysis."},
            "experience": {"score": overall, "feedback": "Add GEMINI_API_KEY for AI analysis."},
            "education":  {"score": overall, "feedback": "Add GEMINI_API_KEY for AI analysis."},
            "projects":   {"score": overall, "feedback": "Add GEMINI_API_KEY for AI analysis."},
        },
        "strengths":               ["Keywords from JD found in resume."],
        "weaknesses":              [f"Missing {len(missing)} keywords from the job description."],
        "improvements":            ["Add a valid GEMINI_API_KEY for AI-powered suggestions."],
        "missing_keywords":        missing[:15],
        "action_verb_suggestions": ["Achieved", "Delivered", "Optimized", "Engineered", "Led"],
        "formatting_tips":         ["Use consistent date formats.", "Add clear section headings."],
        "ats_tips":                ["Include exact keywords from the job description."],
        "recommendation":          rec,
        "recommendation_reason":   (
            f"Your resume matches ~{overall}% of JD keywords. "
            "Enable the Gemini API for a full analysis."
        ),
        "section_audit": {
            s_name: {"keep": ["Relevant content"], "remove": ["Irrelevant items"],
                     "add": ["Quantified achievements"], "improve": ["Stronger action verbs"]}
            for s_name in ("skills", "experience", "education", "projects")
        },
        "bullet_rewrites": [{
            "original": "Worked on projects.",
            "improved": "Engineered 3 end-to-end projects, reducing delivery time by 20%.",
        }],
        "interview_questions": {
            "technical":      ["Describe your technical experience with core tools."],
            "behavioral":     ["Tell me about a time you solved a difficult problem."],
            "project_based":  ["Walk me through your most significant project."],
            "scenario_based": ["How would you approach a tight deadline with unclear requirements?"],
        },
        "learning_roadmap": [
            {"week": i + 1, "topic": skill, "description": f"Study {skill} fundamentals.",
             "skill_category": "Technical"}
            for i, skill in enumerate(missing[:6])
        ],
    }
