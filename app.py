import os
import logging
from flask import Flask
from config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def create_app(env=None):
    app = Flask(__name__)

    env = env or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config.get(env, config["default"]))

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    from routes.main import main_bp
    from routes.analyzer import analyzer_bp
    from routes.report import report_bp
    from routes.company import company_bp
    from routes.compare import compare_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(analyzer_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(compare_bp)

    # Expose Python builtins that Jinja2 doesn't include by default
    app.jinja_env.globals.update(any=any, all=all)

    return app


print("Gemini Key:", os.getenv("GEMINI_API_KEY"))
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
