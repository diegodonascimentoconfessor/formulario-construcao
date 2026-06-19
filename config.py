"""
config.py
Configurações da aplicação separadas por ambiente.
Nunca coloque segredos diretamente aqui; use variáveis de ambiente ou .env.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    # ── Segurança ──────────────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-inseguro-troque-em-producao")
    # Bloqueia payloads JSON acima de 128 KB
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH", 131_072))

    # ── Rate limiting ──────────────────────────────────────────────────────
    RATE_LIMIT_PDF: str     = os.getenv("RATE_LIMIT_PDF",     "10 per minute")
    RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "60 per minute")
    RATELIMIT_STORAGE_URI: str = "memory://"   # troque por Redis em produção

    # ── Headers de segurança ───────────────────────────────────────────────
    # Enviados em toda resposta pelo after_request no __init__.py
    SECURITY_HEADERS: dict = {
        "X-Content-Type-Options":  "nosniff",
        "X-Frame-Options":         "DENY",
        "X-XSS-Protection":        "1; mode=block",
        "Referrer-Policy":         "strict-origin-when-cross-origin",
        "Cache-Control":           "no-store",
        # CSP ampla para desenvolvimento; estreite em produção
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline';"
        ),
    }

    # ── Logging ────────────────────────────────────────────────────────────
    LOG_DIR: str   = os.path.join(os.path.dirname(__file__), "logs")
    LOG_LEVEL: str = "INFO"


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(BaseConfig):
    DEBUG = False
    # Em produção exija HTTPS (habilite HSTS, etc.)
    SECURITY_HEADERS = {
        **BaseConfig.SECURITY_HEADERS,
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    }


_CONFIGS = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
}


def get_config() -> type:
    env = os.getenv("FLASK_ENV", "development")
    return _CONFIGS.get(env, DevelopmentConfig)
