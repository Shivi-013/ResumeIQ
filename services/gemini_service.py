import json
import logging
import re
import google.generativeai as genai

logger = logging.getLogger(__name__)


_PROMPT_TEMPLATE = """You are an expert ATS analyst, career coach, and technical interviewer.

Analyze the resume below against the job description and return ONLY a valid JSON object — no markdown, no code fences, no extra text.

RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Return this exact JSON structure (fill in all values — keep arrays concise, max 6 items each unless noted):
{{
  "overall_score": <integer 0-100>,
  "ats_score": <integer 0-100>,
  "skills_score": <integer 0-100>,
  "experience_score": <integer 0-100>,
  "education_score": <integer 0-100>,
  "required_skills": [<skills required by JD, max 20>],
  "found_skills": [<subset of required_skills present in resume>],
  "missing_skills": [<subset of required_skills absent from resume>],
  "sections": {{
    "skills":     {{"score": <0-100>, "feedback": "<1-2 sentence assessment>"}},
    "experience": {{"score": <0-100>, "feedback": "<1-2 sentence assessment>"}},
    "education":  {{"score": <0-100>, "feedback": "<1-2 sentence assessment>"}},
    "projects":   {{"score": <0-100>, "feedback": "<1-2 sentence assessment>"}}
  }},
  "strengths":               [<4 specific strengths of this resume vs JD>],
  "weaknesses":              [<4 specific gaps or weaknesses>],
  "improvements":            [<5 concrete actionable improvement suggestions>],
  "missing_keywords":        [<important ATS keywords absent from resume, max 10>],
  "action_verb_suggestions": [<5 stronger action verbs to replace weak ones detected>],
  "formatting_tips":         [<3 formatting/structure improvements>],
  "ats_tips":                [<3 ATS optimization tips specific to this resume>],
  "recommendation":          "<exactly one of: Strong Match | Moderate Match | Weak Match>",
  "recommendation_reason":   "<2-3 sentence summary explaining the recommendation>",

  "section_audit": {{
    "skills":     {{"keep": [<1-2 things to keep>], "remove": [<1 thing to remove>], "add": [<2 things to add>], "improve": [<1 thing to improve>]}},
    "experience": {{"keep": [<1-2 things to keep>], "remove": [<1 thing to remove>], "add": [<2 things to add>], "improve": [<1 thing to improve>]}},
    "education":  {{"keep": [<1-2 things to keep>], "remove": [<1 thing to remove>], "add": [<2 things to add>], "improve": [<1 thing to improve>]}},
    "projects":   {{"keep": [<1-2 things to keep>], "remove": [<1 thing to remove>], "add": [<2 things to add>], "improve": [<1 thing to improve>]}}
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
    {{"week": 1, "topic": "<first missing skill>",     "description": "<what to learn and why>", "skill_category": "<Technical|Soft|Tool>"}},
    {{"week": 2, "topic": "<second topic>",            "description": "<what to learn and why>", "skill_category": "<category>"}},
    {{"week": 3, "topic": "<third topic>",             "description": "<what to learn and why>", "skill_category": "<category>"}},
    {{"week": 4, "topic": "<fourth topic>",            "description": "<what to learn and why>", "skill_category": "<category>"}},
    {{"week": 5, "topic": "<fifth topic or review>",   "description": "<what to learn and why>", "skill_category": "<category>"}},
    {{"week": 6, "topic": "<sixth topic or project>",  "description": "<what to learn and why>", "skill_category": "<category>"}}
  ]
}}
"""

# Lighter prompt used for resume comparison mode (faster, no V2 extras)
_COMPARE_PROMPT = """You are an ATS analyst. Analyze this resume vs the job description.
Return ONLY a valid JSON object — no markdown, no code fences.

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
    "experience": {{"score": <0-100>, "feedback": "<brief>"}},
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
    """Full V2 analysis: call Gemini and return complete structured dict."""
    prompt = _PROMPT_TEMPLATE.format(
        resume=resume_text[:8000],
        jd=jd_text[:4000],
    )
    return _call_gemini(prompt, max_tokens=1024)


def analyze_compare(resume_text: str, jd_text: str) -> dict:
    """Lighter analysis for resume comparison mode."""
    prompt = _COMPARE_PROMPT.format(
        resume=resume_text[:6000],
        jd=jd_text[:3000],
    )
    data = _call_gemini(prompt, max_tokens=2048)
    # Ensure V1-compatible keys are present with defaults
    for key in ("improvements", "missing_keywords", "action_verb_suggestions",
                "formatting_tips", "ats_tips", "improvements"):
        data.setdefault(key, [])
    return data


def _call_gemini(prompt: str, max_tokens: int = 8192) -> dict:
    try:
        model = genai.GenerativeModel("gemini-3.5-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=max_tokens,
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
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in Gemini response.")

    data = json.loads(match.group())

    # Clamp scores to 0-100
    for key in ("overall_score", "ats_score", "skills_score", "experience_score", "education_score"):
        data[key] = max(0, min(100, int(data.get(key, 0))))

    # Normalise recommendation
    rec = str(data.get("recommendation", "")).strip()
    if "strong" in rec.lower():
        data["recommendation"] = "Strong Match"
    elif "moderate" in rec.lower():
        data["recommendation"] = "Moderate Match"
    else:
        data["recommendation"] = "Weak Match"

    # Ensure V2 keys have sane defaults if Gemini omitted them
    data.setdefault("section_audit", {})
    data.setdefault("bullet_rewrites", [])
    data.setdefault("interview_questions", {
        "technical": [], "behavioral": [], "project_based": [], "scenario_based": []
    })
    data.setdefault("learning_roadmap", [])

    return data
