"""
app/validators/atendimento.py
Valida e sanitiza o payload JSON do formulário de atendimento.
Toda entrada do usuário passa por aqui antes de tocar qualquer serviço.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import bleach

# ── Constantes permitidas ─────────────────────────────────────────────────────
TIPOS_VALIDOS = {
    "Orçamento", "Pedido de Venda",
    "Requisição Interna", "Devolução", "Entrega Agendada",
}
STATUS_VALIDOS = {"pendente", "aprovado", "entregue", "cancelado"}
PAGAMENTOS_VALIDOS = {
    "À vista", "Boleto 30 dias", "Boleto 30/60",
    "Cartão Débito", "Cartão Crédito", "PIX", "Financiado",
}
CATEGORIAS_VALIDAS = {
    "Cimento e Argamassa", "Areia e Brita", "Tijolos e Blocos",
    "Ferragens", "Hidráulico", "Elétrico", "Tintas", "Madeiras",
    "Cerâmica / Piso", "Telhado", "Ferramentas", "Outros",
}
UNIDADES_VALIDAS = {"un","cx","m","m²","m³","kg","ton","sc","lt","rolo","par","fd"}

MAX_ITENS      = 100
MAX_STR        = 300   # caracteres por campo texto
MAX_OBS        = 2000
MAX_PRICE      = 999_999_999.99
_DATE_RE       = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE       = re.compile(r"^\d{2}:\d{2}$")
_DOC_RE        = re.compile(r"^[\d.\-/]+$")
_PHONE_RE      = re.compile(r"^[\d\s()\-+]+$")


# ── Resultado da validação ────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)

    def fail(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)


# ── Funções auxiliares ────────────────────────────────────────────────────────

def _clean(value: Any, max_len: int = MAX_STR) -> str:
    """Remove tags HTML, normaliza espaços, trunca."""
    if not isinstance(value, str):
        value = str(value) if value is not None else ""
    cleaned = bleach.clean(value, tags=[], strip=True).strip()
    return cleaned[:max_len]


def _require_str(result: ValidationResult, raw: Any, field_name: str,
                 max_len: int = MAX_STR) -> str:
    if not raw or not str(raw).strip():
        result.fail(f"Campo obrigatório ausente: '{field_name}'.")
        return ""
    return _clean(raw, max_len)


def _optional_str(raw: Any, max_len: int = MAX_STR) -> str:
    return _clean(raw, max_len) if raw else ""


def _validate_date(result: ValidationResult, raw: Any, field_name: str) -> str:
    s = _clean(raw or "")
    if s and not _DATE_RE.match(s):
        result.fail(f"'{field_name}' deve estar no formato YYYY-MM-DD.")
    return s


def _validate_number(result: ValidationResult, raw: Any, field_name: str,
                     min_val: float = 0, max_val: float = MAX_PRICE) -> float:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        result.fail(f"'{field_name}' deve ser um número.")
        return 0.0
    if not (min_val <= v <= max_val):
        result.fail(f"'{field_name}' fora do intervalo permitido ({min_val}–{max_val}).")
        return 0.0
    return round(v, 4)


# ── Validador principal ───────────────────────────────────────────────────────

def validate_atendimento(payload: dict) -> ValidationResult:
    """
    Recebe o dict bruto do JSON e devolve ValidationResult.
    Se .ok == True, .data contém o payload limpo e tipado.
    """
    r = ValidationResult()
    d: dict = {}

    # ── Cabeçalho ─────────────────────────────────────────────────────────
    d["num_atend"] = _require_str(r, payload.get("num_atend"), "num_atend")
    d["tipo"]      = _optional_str(payload.get("tipo"))
    if d["tipo"] and d["tipo"] not in TIPOS_VALIDOS:
        r.fail(f"'tipo' inválido: '{d['tipo']}'.")

    d["data"]      = _validate_date(r, payload.get("data"), "data")
    hora = _clean(payload.get("hora") or "")
    if hora and not _TIME_RE.match(hora):
        r.fail("'hora' deve estar no formato HH:MM.")
    d["hora"] = hora

    d["vendedor"]  = _optional_str(payload.get("vendedor"))

    status = _clean(payload.get("status") or "pendente").lower()
    if status not in STATUS_VALIDOS:
        r.fail(f"'status' inválido: '{status}'.")
    d["status"] = status

    # ── Cliente ───────────────────────────────────────────────────────────
    cli_raw = payload.get("cliente") or {}
    if not isinstance(cli_raw, dict):
        r.fail("'cliente' deve ser um objeto.")
        cli_raw = {}

    nome = _require_str(r, cli_raw.get("nome"), "cliente.nome")

    doc = _clean(cli_raw.get("doc") or "")
    if doc and not _DOC_RE.match(doc):
        r.fail("'cliente.doc' contém caracteres inválidos.")

    tel = _clean(cli_raw.get("tel") or "")
    if tel and not _PHONE_RE.match(tel):
        r.fail("'cliente.tel' contém caracteres inválidos.")

    d["cliente"] = {
        "nome":   nome,
        "doc":    doc,
        "tel":    tel,
        "email":  _optional_str(cli_raw.get("email")),
        "obra":   _optional_str(cli_raw.get("obra")),
        "end":    _optional_str(cli_raw.get("end")),
        "bairro": _optional_str(cli_raw.get("bairro")),
        "cidade": _optional_str(cli_raw.get("cidade")),
    }

    # ── Itens ─────────────────────────────────────────────────────────────
    itens_raw = payload.get("itens")
    if not isinstance(itens_raw, list):
        r.fail("'itens' deve ser uma lista.")
        itens_raw = []
    if len(itens_raw) > MAX_ITENS:
        r.fail(f"Número de itens excede o limite de {MAX_ITENS}.")
        itens_raw = itens_raw[:MAX_ITENS]

    itens: list[dict] = []
    for idx, item in enumerate(itens_raw):
        if not isinstance(item, dict):
            r.fail(f"Item #{idx+1}: formato inválido.")
            continue

        cat = _optional_str(item.get("cat"))
        if cat and cat not in CATEGORIAS_VALIDAS:
            cat = "Outros"

        un = _clean(item.get("un") or "un")
        if un not in UNIDADES_VALIDAS:
            un = "un"

        qtd   = _validate_number(r, item.get("qtd",0),   f"item[{idx+1}].qtd",   0, 1_000_000)
        preco = _validate_number(r, item.get("preco",0), f"item[{idx+1}].preco",  0, MAX_PRICE)
        total = round(qtd * preco, 2)

        itens.append({
            "desc":  _optional_str(item.get("desc")),
            "cat":   cat,
            "un":    un,
            "qtd":   qtd,
            "preco": preco,
            "total": total,
        })
    d["itens"] = itens

    # ── Totais ────────────────────────────────────────────────────────────
    d["desconto"] = _validate_number(r, payload.get("desconto", 0), "desconto", 0, 100)
    d["frete"]    = _validate_number(r, payload.get("frete", 0),    "frete",    0, MAX_PRICE)

    # ── Condições ─────────────────────────────────────────────────────────
    pagamento = _optional_str(payload.get("pagamento"))
    if pagamento and pagamento not in PAGAMENTOS_VALIDOS:
        pagamento = "À vista"
    d["pagamento"] = pagamento
    d["prazo"]     = _optional_str(payload.get("prazo"))
    d["validade"]  = _validate_date(r, payload.get("validade"), "validade")

    # ── Observações ───────────────────────────────────────────────────────
    d["obs"] = _optional_str(payload.get("obs"), MAX_OBS)

    r.data = d
    return r
