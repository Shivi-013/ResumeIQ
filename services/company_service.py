import logging
import google.generativeai as genai
from services.gemini_service import _parse_response

logger = logging.getLogger(__name__)

COMPANIES = {
    "Google": {
        "label": "Google",
        "focus": (
            "strong algorithms & data structures, system design at scale, clean code quality, "
            "strong problem-solving ability (LeetCode-style), Googleyness & leadership, "
            "experience with distributed systems or large-scale software"
        ),
        "traits": ["Algorithms & Data Structures", "System Design", "Code Quality",
                   "Problem Solving", "Scalability", "Googleyness"],
    },
    "Amazon": {
        "label": "Amazon",
        "focus": (
            "Amazon Leadership Principles (Customer Obsession, Ownership, Invent & Simplify, "
            "Bias for Action, Frugality, Earn Trust, Dive Deep, Think Big, Deliver Results), "
            "system design for scale, data-driven decision making, operational excellence"
        ),
        "traits": ["Leadership Principles", "Customer Obsession", "System Design",
                   "Ownership Mindset", "Data-Driven", "Operational Excellence"],
    },
    "Microsoft": {
        "label": "Microsoft",
        "focus": (
            "growth mindset, Azure/cloud expertise, cross-team collaboration, technical breadth "
            "across full stack, inclusive design, security-first thinking, DevOps practices"
        ),
        "traits": ["Growth Mindset", "Azure/Cloud", "Collaboration", "Full-Stack Breadth",
                   "Security Awareness", "DevOps"],
    },
    "Netflix": {
        "label": "Netflix",
        "focus": (
            "freedom & responsibility culture, high performance and direct impact, "
            "self-direction and autonomy, innovation and experimentation, streaming/video "
            "domain knowledge, strong communication and async work"
        ),
        "traits": ["High Performance", "Autonomy", "Direct Impact", "Innovation",
                   "Streaming Domain", "Strong Communication"],
    },
    "Meta": {
        "label": "Meta",
        "focus": (
            "move fast culture, social-scale systems, data-driven product thinking, "
            "mobile-first development, open source contributions, cross-functional impact, "
            "React/React Native experience, ML/AI product experience"
        ),
        "traits": ["Move Fast", "Social Scale", "Mobile-First", "Data-Driven",
                   "React/RN", "ML/AI Experience"],
    },
}

_COMPANY_PROMPT = """You are a senior talent acquisition specialist at {company}.

Evaluate this candidate's resume against typical {company} hiring expectations.
Consider: {focus}

RESUME: {resume}
JOB DESCRIPTION: {jd}

Return ONLY a valid JSON object — no markdown, no code fences:
{{
  "company": "{company}",
  "company_match_score": <integer 0-100>,
  "key_traits_required": {traits},
  "traits_present": [<which key traits are evident in the resume>],
  "traits_missing": [<which key traits are absent>],
  "specific_feedback": [<3-4 company-specific improvement suggestions>],
  "hiring_likelihood": "<High|Medium|Low>",
  "recommendation": "<2-3 sentences on candidacy fit for {company}>"
}}
"""


def analyze_for_company(
    company_key: str,
    resume_text: str,
    jd_text: str,
) -> dict:
    """
    Run a company-specific analysis using Gemini.
    Returns a dict with company match details, or raises RuntimeError.
    """
    profile = COMPANIES.get(company_key)
    if not profile:
        raise ValueError(f"Unknown company key: {company_key!r}")

    prompt = _COMPANY_PROMPT.format(
        company=profile["label"],
        focus=profile["focus"],
        traits=str(profile["traits"]),
        resume=resume_text[:6000],
        jd=jd_text[:3000],
    )

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2048,
                response_mime_type="application/json",
            ),
        )
        data = _parse_response(response.text)

        # Normalise hiring_likelihood
        hl = str(data.get("hiring_likelihood", "")).strip().capitalize()
        data["hiring_likelihood"] = hl if hl in ("High", "Medium", "Low") else "Medium"

        # Clamp score
        data["company_match_score"] = max(0, min(100, int(data.get("company_match_score", 0))))

        return data
    except Exception as exc:
        logger.error("Company analysis failed for %s: %s", company_key, exc)
        raise RuntimeError(f"Company analysis failed: {exc}") from exc
