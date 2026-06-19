"""
app/routes/main.py
Rota principal — serve o formulário HTML.
"""
import os

from flask import Blueprint, current_app, abort

main_bp = Blueprint("main", __name__)

_HTML_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "static", "formulario_construcao.html"
)


@main_bp.route("/", methods=["GET"])
def index():
    html_file = os.path.abspath(_HTML_PATH)
    if not os.path.isfile(html_file):
        current_app.logger.error("HTML não encontrado: %s", html_file)
        abort(404, "Formulário não encontrado.")
    with open(html_file, encoding="utf-8") as fh:
        content = fh.read()
    return content, 200, {"Content-Type": "text/html; charset=utf-8"}
