import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    ALLOWED_EXTENSIONS = {"pdf"}
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
