"""
app/__init__.py
Application factory.  Toda extensão e todo blueprint é registrado aqui,
mantendo o app.py de entrada limpo e facilitando testes unitários.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import get_config

# Instância global do limiter (configurada na factory)
limiter = Limiter(key_func=get_remote_address)


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    cfg = get_config()
    app.config.from_object(cfg)

    # ── Extensões ──────────────────────────────────────────────────────────
    limiter.init_app(app)

    # ── Logging ────────────────────────────────────────────────────────────
    _setup_logging(app)

    # ── Blueprints ─────────────────────────────────────────────────────────
    from app.routes.main import main_bp
    from app.routes.pdf  import pdf_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(pdf_bp)

    # ── Headers de segurança em toda resposta ──────────────────────────────
    @app.after_request
    def apply_security_headers(response):
        for header, value in app.config["SECURITY_HEADERS"].items():
            response.headers[header] = value
        return response

    # ── Tratamento global de erros ─────────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        app.logger.warning("400 %s — %s", request.path, str(e))
        return jsonify(error=str(e)), 400

    @app.errorhandler(413)
    def payload_too_large(_e):
        app.logger.warning("413 payload too large — %s", request.path)
        return jsonify(error="Payload muito grande. Limite: 128 KB."), 413

    @app.errorhandler(429)
    def rate_limit_hit(e):
        app.logger.warning("429 rate-limit — %s %s", request.remote_addr, request.path)
        return jsonify(error="Muitas requisições. Aguarde e tente novamente."), 429

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error("500 %s — %s", request.path, str(e), exc_info=True)
        return jsonify(error="Erro interno. Tente novamente."), 500

    return app


# ── Helpers ───────────────────────────────────────────────────────────────────

def _setup_logging(app: Flask) -> None:
    level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO)
    fmt   = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Arquivo rotativo (5 MB × 3 backups)
    # Console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(level)

    app.logger.handlers.clear()
    app.logger.addHandler(console_handler)

    if app.config.get("LOG_TO_FILE", True):
        log_dir = app.config["LOG_DIR"]
        os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        file_handler.setLevel(level)
        app.logger.addHandler(file_handler)

    app.logger.setLevel(level)
