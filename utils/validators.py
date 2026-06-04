import os

ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MIN_JD_LENGTH = 100
MAX_JD_LENGTH = 5000


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_pdf(file) -> tuple[bool, str]:
    """Return (is_valid, error_message). Empty error means valid."""
    if not file or file.filename == "":
        return False, "No file selected."
    if not allowed_file(file.filename):
        return False, "Only PDF files are allowed."
    # Read a small chunk to check magic bytes (%PDF)
    header = file.read(4)
    file.seek(0)
    if header != b"%PDF":
        return False, "File does not appear to be a valid PDF."
    return True, ""


def validate_jd(text: str) -> tuple[bool, str]:
    """Validate job description text."""
    if not text or not text.strip():
        return False, "Job description cannot be empty."
    stripped = text.strip()
    if len(stripped) < MIN_JD_LENGTH:
        return False, f"Job description must be at least {MIN_JD_LENGTH} characters."
    if len(stripped) > MAX_JD_LENGTH:
        return False, f"Job description must not exceed {MAX_JD_LENGTH} characters."
    return True, ""
