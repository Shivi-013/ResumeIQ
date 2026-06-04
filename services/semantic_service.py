import logging

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def compute_similarity(text1: str, text2: str) -> float | None:
    """
    Compute semantic similarity between resume and JD texts.
    Returns a score 0–100, or None if sentence-transformers is unavailable.
    """
    try:
        from sentence_transformers import util
        model = _get_model()
        emb1 = model.encode(text1[:3000], convert_to_tensor=True)
        emb2 = model.encode(text2[:3000], convert_to_tensor=True)
        score = util.pytorch_cos_sim(emb1, emb2).item()
        return round(max(0.0, min(1.0, score)) * 100, 1)
    except Exception as exc:
        logger.warning("Semantic similarity unavailable: %s", exc)
        return None
