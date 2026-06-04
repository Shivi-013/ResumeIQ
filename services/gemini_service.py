import json
import logging
import re
import google.generativeai as genai

logger = logging.getLogger(__name__)


_PROMPT_TEMPLATE = """You are an expert ATS analyst, career coach, and technical interviewer.

IMPORTANT CONTEXT: This may be a student or early-career resume. If the candidate has no formal work experience, treat strong academic projects, hackathons, internships, open-source contributions, or freelance work as valid experience. Score and comment accordingly — do NOT penalise a student for lacking full-time experience if their projects demonstrate the required skills.

Analyze the resume below against the job description and return a valid JSON object.

RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Return this exact JSON structure (fill in all values — keep arrays concise, max 6 items each unless noted):
{{
  "overall_score": <integer 0-100>,
  "ats_score": <integer 0-100>,
  "skills_score": <integer 0-100>,
  "experience_score": <integer 0-100, treat projects/internships as experience for students>,
  "education_score": <integer 0-100>,
  "required_skills": [<skills required by JD, max 20>],
  "found_skills": [<subset of required_skills present in resume>],
  "missing_skills": [<subset of required_skills absent from resume>],
  "sections": {{
    "skills":     {{"score": <0-100>, "feedback": "<1-2 sentence honest assessment, mention projects if no formal experience>"}},
    "experience": {{"score": <0-100>, "feedback": "<1-2 sentence honest assessment, acknowledge projects/internships if no full-time work>"}},
    "education":  {{"score": <0-100>, "feedback": "<1-2 sentence assessment>"}},
    "projects":   {{"score": <0-100>, "feedback": "<1-2 sentence assessment, highlight if projects substitute for experience>"}}
  }},
  "strengths":               [<4 specific strengths of this resume vs JD>],
  "weaknesses":              [<4 specific gaps or weaknesses>],
  "improvements":            [<5 concrete actionable improvement suggestions>],
  "missing_keywords":        [<important ATS keywords absent from resume, max 10>],
  "action_verb_suggestions": [<5 stronger action verbs to replace weak ones detected>],
  "formatting_tips":         [<3 formatting/structure improvements>],
  "ats_tips":                [<3 ATS optimization tips specific to this resume>],
  "recommendation":          "<exactly one of: Strong Match | Moderate Match | Weak Match>",
  "recommendation_reason":   "<2-3 sentence summary — if student, acknowledge project strength compensating for lack of experience>",

  "section_audit": {{
    "skills":     {{"keep": [<1-2 things to keep>], "remove": [<1 thing to remove or 'Nothing to remove'>], "add": [<2 things to add>], "improve": [<1 thing to improve>]}},
    "experience": {{"keep": [<1-2 things to keep>], "remove": [<1 thing to remove or 'Nothing to remove'>], "add": [<2 things to add>], "improve": [<1 thing to improve>]}},
    "education":  {{"keep": [<1-2 things to keep>], "remove": [<1 thing to remove or 'Nothing to remove'>], "add": [<2 things to add>], "improve": [<1 thing to improve>]}},
    "projects":   {{"keep": [<1-2 things to keep>], "remove": [<1 thing to remove or 'Nothing to remove'>], "add": [<2 things to add>], "improve": [<1 thing to improve>]}}
  }},

  "bullet_rewrites": [
    {{"original": "<an actual weak bullet from the resume>", "improved": "<rewritten with strong action verb + quantified impact>"}},
    {{"original": "<another weak bullet>", "improved": "<rewritten>"}},
    {{"original": "<another weak bullet>", "improved": "<rewritten>"}},
    {{"original": "<another weak bullet>", "improved": "<rewritten>"}},
    {{"original": "<another weak bullet>", "improved": "<rewritten>"}}
  ],

  "interview_questions": {{
    "technical":     [<3 technical questions based on skills in JD>],
    "behavioral":    [<3 behavioral questions based on role requirements>],
    "project_based": [<2 questions about specific projects in resume>],
    "scenario_based":[<2 situational questions relevant to the role>]
  }},

  "learning_roadmap": [
    {{"week": 1, "topic": "<first missing skill>",    "description": "<what to learn and why>", "skill_category": "<Technical|Soft|Tool>"}},
    {{"week": 2, "topic": "<second topic>",           "description": "<what to learn and why>", "skill_category": "<category>"}},
    {{"week": 3, "topic": "<third topic>",            "description": "<what to learn and why>", "skill_category": "<category>"}},
    {{"week": 4, "topic": "<fourth topic>",           "description": "<what to learn and why>", "skill_category": "<category>"}},
    {{"week": 5, "topic": "<fifth topic or review>",  "description": "<what to learn and why>", "skill_category": "<category>"}},
    {{"week": 6, "topic": "<sixth topic or project>", "description": "<what to learn and why>", "skill_category": "<category>"}}
  ]
}}
"""

# Lighter prompt for resume comparison mode
_COMPARE_PROMPT = """You are an ATS analyst. If the candidate is a student, treat projects and internships as valid experience.
Analyze this resume vs the job description and return a valid JSON object.

RESUME: {resume}
JOB DESCRIPTION: {jd}

Return:
{{
  "overall_score": <0-100>,
  "ats_score": <0-100>,
  "skills_score": <0-100>,
  "experience_score": <0-100>,
  "education_score": <0-100>,
  "required_skills": [<max 15 skills from JD>],
  "found_skills": [<skills present in resume>],
  "missing_skills": [<skills absent from resume>],
  "sections": {{
    "skills":     {{"score": <0-100>, "feedback": "<brief>"}},
    "experience": {{"score": <0-100>, "feedback": "<brief, credit projects if student>"}},
    "education":  {{"score": <0-100>, "feedback": "<brief>"}},
    "projects":   {{"score": <0-100>, "feedback": "<brief>"}}
  }},
  "strengths":   [<3 strengths>],
  "weaknesses":  [<3 weaknesses>],
  "recommendation": "<Strong Match|Moderate Match|Weak Match>",
  "recommendation_reason": "<1 sentence>"
}}
"""


def configure(api_key: str) -> None:
    genai.configure(api_key=api_key)


def analyze(resume_text: str, jd_text: str) -> dict:
    """Full V2 analysis."""
    prompt = _PROMPT_TEMPLATE.format(
        resume=resume_text[:8000],
        jd=jd_text[:4000],
    )
    return _call_gemini(prompt, max_tokens=8192)


def analyze_compare(resume_text: str, jd_text: str) -> dict:
    """Lighter analysis for resume comparison mode."""
    prompt = _COMPARE_PROMPT.format(
        resume=resume_text[:6000],
        jd=jd_text[:3000],
    )
    data = _call_gemini(prompt, max_tokens=2048)
    for key in ("improvements", "missing_keywords", "action_verb_suggestions",
                "formatting_tips", "ats_tips"):
        data.setdefault(key, [])
    return data


def _call_gemini(prompt: str, max_tokens: int = 8192) -> dict:
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
            ),
        )
        raw = response.text
        logger.debug("Gemini raw response length: %d", len(raw))
        return _parse_response(raw)
    except Exception as exc:
        logger.error("Gemini API error: %s", exc)
        raise RuntimeError(f"Gemini API call failed: {exc}") from exc


def _parse_response(raw: str) -> dict:
    """Extract and validate JSON from Gemini's response."""
    # Strip thinking tokens (gemini-2.5 with thinking enabled)
    raw = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)
    # Strip markdown fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = re.sub(r"```\s*", "", cleaned).strip()

    # Try direct parse first (fastest path when response_mime_type works)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fall back to regex extraction
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in Gemini response.")
        data = json.loads(match.group())

    # Clamp scores to 0-100
    for key in ("overall_score", "ats_score", "skills_score",
                "experience_score", "education_score"):
        data[key] = max(0, min(100, int(data.get(key, 0))))

    # Normalise recommendation
    rec = str(data.get("recommendation", "")).strip()
    if "strong" in rec.lower():
        data["recommendation"] = "Strong Match"
    elif "moderate" in rec.lower():
        data["recommendation"] = "Moderate Match"
    else:
        data["recommendation"] = "Weak Match"

    # V2 key defaults
    data.setdefault("section_audit", {})
    data.setdefault("bullet_rewrites", [])
    data.setdefault("interview_questions", {
        "technical": [], "behavioral": [], "project_based": [], "scenario_based": []
    })
    data.setdefault("learning_roadmap", [])

    return data
