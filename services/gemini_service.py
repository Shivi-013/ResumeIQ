import json
import logging
import re
import google.generativeai as genai

logger = logging.getLogger(__name__)


_PROMPT_TEMPLATE = """You are an expert ATS analyst, career coach, and technical interviewer.

IMPORTANT: If the candidate is a student or early-career, treat projects, internships, hackathons, and open-source contributions as valid experience. Do NOT penalise missing full-time work if projects demonstrate the required skills.

Analyze the resume below against the job description.
Return ONLY a raw JSON object. No markdown, no code fences, no explanation, no text before or after the JSON.

RESUME:
{resume}

JOB DESCRIPTION:
{jd}

JSON structure to return:
{{
  "overall_score": 0,
  "ats_score": 0,
  "skills_score": 0,
  "experience_score": 0,
  "education_score": 0,
  "required_skills": [],
  "found_skills": [],
  "missing_skills": [],
  "sections": {{
    "skills":     {{"score": 0, "feedback": ""}},
    "experience": {{"score": 0, "feedback": "credit projects/internships if student"}},
    "education":  {{"score": 0, "feedback": ""}},
    "projects":   {{"score": 0, "feedback": ""}}
  }},
  "strengths": [],
  "weaknesses": [],
  "improvements": [],
  "missing_keywords": [],
  "action_verb_suggestions": [],
  "formatting_tips": [],
  "ats_tips": [],
  "recommendation": "Strong Match",
  "recommendation_reason": "",
  "section_audit": {{
    "skills":     {{"keep": [], "remove": [], "add": [], "improve": []}},
    "experience": {{"keep": [], "remove": [], "add": [], "improve": []}},
    "education":  {{"keep": [], "remove": [], "add": [], "improve": []}},
    "projects":   {{"keep": [], "remove": [], "add": [], "improve": []}}
  }},
  "bullet_rewrites": [
    {{"original": "", "improved": ""}},
    {{"original": "", "improved": ""}},
    {{"original": "", "improved": ""}},
    {{"original": "", "improved": ""}},
    {{"original": "", "improved": ""}}
  ],
  "interview_questions": {{
    "technical": [],
    "behavioral": [],
    "project_based": [],
    "scenario_based": []
  }},
  "learning_roadmap": [
    {{"week": 1, "topic": "", "description": "", "skill_category": "Technical"}},
    {{"week": 2, "topic": "", "description": "", "skill_category": "Technical"}},
    {{"week": 3, "topic": "", "description": "", "skill_category": "Technical"}},
    {{"week": 4, "topic": "", "description": "", "skill_category": "Tool"}},
    {{"week": 5, "topic": "", "description": "", "skill_category": "Tool"}},
    {{"week": 6, "topic": "", "description": "", "skill_category": "Soft"}}
  ]
}}

Rules:
- All scores are integers 0-100.
- required_skills: max 20 items.
- missing_keywords: max 10 items.
- strengths, weaknesses, improvements: 4-5 items each.
- action_verb_suggestions, formatting_tips, ats_tips: 3-5 items each.
- Each interview_questions list: 2-3 items.
- learning_roadmap: 6 weeks based on the missing skills.
- bullet_rewrites: use actual weak bullets from the resume. Keep strings short — avoid unescaped quotes inside strings.
- recommendation must be exactly one of: Strong Match | Moderate Match | Weak Match
"""

_COMPARE_PROMPT = """You are an ATS analyst. Treat projects and internships as valid experience for students.
Analyze this resume vs the job description. Return ONLY a raw JSON object, no markdown, no extra text.

RESUME: {resume}
JOB DESCRIPTION: {jd}

Return:
{{
  "overall_score": 0,
  "ats_score": 0,
  "skills_score": 0,
  "experience_score": 0,
  "education_score": 0,
  "required_skills": [],
  "found_skills": [],
  "missing_skills": [],
  "sections": {{
    "skills":     {{"score": 0, "feedback": ""}},
    "experience": {{"score": 0, "feedback": ""}},
    "education":  {{"score": 0, "feedback": ""}},
    "projects":   {{"score": 0, "feedback": ""}}
  }},
  "strengths": [],
  "weaknesses": [],
  "recommendation": "Moderate Match",
  "recommendation_reason": ""
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
            ),
        )
        raw = response.text
        logger.info("Gemini response length: %d chars", len(raw))
        return _parse_response(raw)
    except Exception as exc:
        logger.error("Gemini API error: %s", exc)
        raise RuntimeError(f"Gemini API call failed: {exc}") from exc


def _parse_response(raw: str) -> dict:
    """
    Robustly extract and validate JSON from Gemini's response.
    Handles: thinking tags, markdown fences, leading/trailing text,
    truncated JSON (recovers the partial object).
    """
    if not raw:
        raise ValueError("Empty response from Gemini.")

    # 1. Strip thinking tokens (gemini-2.5 thinking variant)
    text = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)

    # 2. Strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*", "", text).strip()

    # 3. Try direct parse (cleanest path)
    try:
        data = json.loads(text)
        return _validate(data)
    except json.JSONDecodeError:
        pass

    # 4. Extract from surrounding text using the outermost { }
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            return _validate(data)
        except json.JSONDecodeError:
            pass

    # 5. Attempt truncation recovery — close any open brackets and retry
    recovered = _recover_truncated_json(text)
    if recovered:
        try:
            data = json.loads(recovered)
            return _validate(data)
        except json.JSONDecodeError:
            pass

    # 6. Log what we actually got so we can diagnose in Render logs
    logger.warning("Could not parse Gemini response. First 500 chars: %s", raw[:500])
    raise ValueError("No valid JSON object found in Gemini response.")


def _recover_truncated_json(text: str) -> str | None:
    """
    Try to close a truncated JSON string by counting open brackets/braces
    and appending the missing closers.
    """
    start = text.find("{")
    if start == -1:
        return None

    fragment = text[start:]
    stack = []
    in_string = False
    escape_next = False

    for ch in fragment:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if stack and stack[-1] == ch:
                stack.pop()

    if not stack:
        return None  # Already valid — parser should have caught it

    # Close any open string first, then close the brackets
    suffix = ('"' if in_string else "") + "".join(reversed(stack))
    return fragment + suffix


def _validate(data: dict) -> dict:
    """Clamp scores, normalise recommendation, fill V2 defaults."""
    for key in ("overall_score", "ats_score", "skills_score",
                "experience_score", "education_score"):
        data[key] = max(0, min(100, int(data.get(key, 0))))

    rec = str(data.get("recommendation", "")).strip()
    if "strong" in rec.lower():
        data["recommendation"] = "Strong Match"
    elif "moderate" in rec.lower():
        data["recommendation"] = "Moderate Match"
    else:
        data["recommendation"] = "Weak Match"

    data.setdefault("section_audit", {})
    data.setdefault("bullet_rewrites", [])
    data.setdefault("interview_questions", {
        "technical": [], "behavioral": [], "project_based": [], "scenario_based": []
    })
    data.setdefault("learning_roadmap", [])
    return data
