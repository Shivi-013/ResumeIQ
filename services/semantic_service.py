import logging
import re

logger = logging.getLogger(__name__)


def compute_similarity(text1: str, text2: str) -> float | None:
    """
    Compute semantic similarity between resume and JD texts using TF-IDF
    cosine similarity (sklearn). Returns 0–100 or None on failure.

    Uses sklearn instead of sentence-transformers to stay within Render's
    512 MB memory limit (torch alone consumes ~350 MB).
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        t1 = _clean(text1[:4000])
        t2 = _clean(text2[:4000])
        if not t1 or not t2:
            return None

        vec = TfidfVectorizer(stop_words="english", max_features=8000)
        tfidf = vec.fit_transform([t1, t2])
        score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return round(float(score) * 100, 1)
    except Exception as exc:
        logger.warning("Semantic similarity unavailable: %s", exc)
        return None


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()
