"""
app/utils/security.py
Utilitários de segurança reutilizáveis.
"""
from __future__ import annotations

import re
import unicodedata


_SAFE_FILENAME_RE = re.compile(r"[^\w\-.]")


def safe_filename(name: str, fallback: str = "atendimento") -> str:
    """
    Converte uma string para um nome de arquivo seguro:
    - normaliza unicode (remove acentos)
    - remove caracteres fora de [a-zA-Z0-9_.-]
    - limita a 80 caracteres
    """
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    safe = _SAFE_FILENAME_RE.sub("_", ascii_str).strip("_")
    return (safe[:80] or fallback)


def is_safe_json_content_type(content_type: str) -> bool:
    """Verifica se o Content-Type é application/json."""
    return "application/json" in (content_type or "").lower()
