"""
app/routes/pdf.py
Rota POST /gerar_pdf.

Fluxo de segurança:
  1. Verifica Content-Type
  2. Verifica tamanho do payload (MAX_CONTENT_LENGTH já bloqueia via Flask)
  3. Valida/sanitiza com o validator
  4. Gera o PDF no service
  5. Devolve como attachment com nome seguro
"""
import io

from flask import Blueprint, current_app, jsonify, request, send_file

from app import limiter
from app.services.pdf_service import build_pdf
from app.utils.security import is_safe_json_content_type, safe_filename
from app.validators.atendimento import validate_atendimento

pdf_bp = Blueprint("pdf", __name__)


@pdf_bp.route("/gerar_pdf", methods=["POST"])
@limiter.limit(lambda: current_app.config["RATE_LIMIT_PDF"])
def gerar_pdf():
    # ── 1. Content-Type ───────────────────────────────────────────────────
    if not is_safe_json_content_type(request.content_type):
        current_app.logger.warning(
            "Content-Type inválido em /gerar_pdf: %s", request.content_type
        )
        return jsonify(error="Content-Type deve ser application/json."), 415

    # ── 2. Parse JSON ─────────────────────────────────────────────────────
    payload = request.get_json(silent=True)
    if payload is None:
        current_app.logger.warning("JSON inválido ou vazio em /gerar_pdf")
        return jsonify(error="JSON inválido ou vazio."), 400

    # ── 3. Validação / sanitização ────────────────────────────────────────
    result = validate_atendimento(payload)
    if not result.ok:
        current_app.logger.info(
            "Payload rejeitado — %d erro(s): %s",
            len(result.errors), result.errors
        )
        return jsonify(errors=result.errors), 422

    # ── 4. Geração do PDF ─────────────────────────────────────────────────
    try:
        pdf_bytes = build_pdf(result.data)
    except Exception as exc:
        current_app.logger.error("Erro ao gerar PDF: %s", exc, exc_info=True)
        return jsonify(error="Falha na geração do PDF."), 500

    # ── 5. Resposta ───────────────────────────────────────────────────────
    num = result.data.get("num_atend", "doc")
    filename = safe_filename(f"atendimento_{num}") + ".pdf"
    current_app.logger.info("PDF gerado com sucesso: %s", filename)

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )
