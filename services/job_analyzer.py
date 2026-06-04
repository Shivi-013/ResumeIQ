import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# Common English stopwords to filter out of keyword extraction
_STOPWORDS = {
    "a","an","the","and","or","but","if","in","on","at","to","for","of","with",
    "by","from","as","is","was","are","were","be","been","being","have","has",
    "had","do","does","did","will","would","could","should","may","might","shall",
    "can","need","must","we","our","you","your","they","their","it","its","this",
    "that","these","those","i","my","me","us","he","she","him","her","who","which",
    "what","when","where","how","all","any","both","each","few","more","most",
    "other","some","such","no","not","only","same","so","than","too","very",
    "just","about","above","after","before","between","during","through","within",
    "without","also","including","required","preferred","experience","ability",
    "strong","excellent","good","great","working","work","role","team","position",
    "candidate","looking","seeking","responsible","responsibilities","duties",
    "provide","ensure","support","develop","maintain","manage","create","build",
    "using","use","well","plus","bonus","knowledge","understanding","familiarity",
    "least","years","year","minimum","background","skills","skill","ability",
    "requirements","requirement","qualifications","qualification","equivalent",
    "related","field","degree","bachelor","master","phd","proven","demonstrated",
    "ability","abilities","proficiency","proficient","familiar","familiarity",
    "company","organization","environment","based","hands","across","within",
    "etc","ie","eg","including","including","like","similar","new","help",
    "world","leading","top","best","fast","growing","key","main","primary",
}


def clean_text(text: str) -> str:
    """Normalize whitespace and remove non-ASCII garbage."""
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_keywords(text: str) -> List[str]:
    """
    Extract meaningful keywords from a job description.
    Returns a deduplicated lowercase list, sorted alphabetically.
    """
    text = clean_text(text.lower())
    # Keep only alphabetic tokens (2+ chars) and hyphenated terms
    tokens = re.findall(r"[a-z][a-z\-\.#+]{1,}", text)

    seen: set[str] = set()
    keywords: List[str] = []
    for token in tokens:
        # Normalise: strip trailing punctuation
        token = token.strip(".-")
        if token and token not in _STOPWORDS and token not in seen:
            seen.add(token)
            keywords.append(token)

    return sorted(keywords)


def compute_keyword_coverage(resume_text: str, required_skills: List[str]) -> List[dict]:
    """
    For each required skill from Gemini's analysis, count occurrences in the resume.
    Returns a list of dicts suitable for the keyword coverage chart and visual bars.

    Levels:
      strong  — 3+ occurrences  → bar_pct 100
      medium  — 1-2 occurrences → bar_pct 55
      missing — 0 occurrences   → bar_pct 0
    """
    resume_lower = resume_text.lower()
    coverage = []
    for skill in required_skills[:25]:  # cap to avoid huge lists
        pattern = re.compile(r"\b" + re.escape(skill.lower()) + r"\b")
        count = len(pattern.findall(resume_lower))
        if count >= 3:
            level, bar_pct = "strong", 100
        elif count >= 1:
            level, bar_pct = "medium", 55
        else:
            level, bar_pct = "missing", 0
        coverage.append({
            "skill": skill,
            "count": count,
            "level": level,
            "bar_pct": bar_pct,
        })
    # Sort: strong first, then medium, then missing
    order = {"strong": 0, "medium": 1, "missing": 2}
    coverage.sort(key=lambda x: order[x["level"]])
    return coverage


def calculate_keyword_overlap(resume_text: str, jd_keywords: List[str]) -> dict:
    """
    Fallback local scoring when Gemini is unavailable.
    Returns found/missing skills and a rough overlap percentage.
    """
    resume_lower = resume_text.lower()
    found = [kw for kw in jd_keywords if re.search(r"\b" + re.escape(kw) + r"\b", resume_lower)]
    missing = [kw for kw in jd_keywords if kw not in found]

    total = len(jd_keywords) if jd_keywords else 1
    score = round(len(found) / total * 100)

    return {
        "found_skills": found,
        "missing_skills": missing,
        "skills_score": score,
    }
