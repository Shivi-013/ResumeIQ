import logging
import re
from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_text(file_path: str) -> str:
    """Extract and clean text from a PDF file."""
    try:
        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        raw = "\n".join(pages)
        return _clean_text(raw)
    except Exception as exc:
        logger.error("PDF extraction failed for %s: %s", file_path, exc)
        raise ValueError(f"Could not read PDF: {exc}") from exc


def _clean_text(text: str) -> str:
    # Collapse multiple blank lines to one
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple spaces to one
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()
