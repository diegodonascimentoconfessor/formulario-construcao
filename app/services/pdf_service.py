"""
app/services/pdf_service.py
Toda lógica de geração de PDF em um único lugar.
Recebe o dict já validado e devolve bytes do PDF.
"""
from __future__ import annotations

import datetime
import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ── Paleta ─────────────────────────────────────────────────────────────────
VERDE       = colors.HexColor("#1F3A2D")
TIJOLO      = colors.HexColor("#C05E1A")
CINZA_CL    = colors.HexColor("#F0EDE8")
CINZA_BD    = colors.HexColor("#D9D4CB")
BRANCO      = colors.white
PRETO       = colors.HexColor("#1A1916")
MUTED       = colors.HexColor("#6B6560")

_STATUS_FG: dict[str, colors.Color] = {
    "pendente":  colors.HexColor("#92400E"),
    "aprovado":  colors.HexColor("#14532D"),
    "entregue":  colors.HexColor("#1E3A8A"),
    "cancelado": colors.HexColor("#7F1D1D"),
}
_STATUS_BG: dict[str, colors.Color] = {
    "pendente":  colors.HexColor("#FEF3C7"),
    "aprovado":  colors.HexColor("#DCFCE7"),
    "entregue":  colors.HexColor("#DBEAFE"),
    "cancelado": colors.HexColor("#FEE2E2"),
}
_STATUS_LABEL: dict[str, str] = {
    "pendente": "PENDENTE", "aprovado": "APROVADO",
    "entregue": "ENTREGUE", "cancelado": "CANCELADO",
}


# ── Estilos ─────────────────────────────────────────────────────────────────

def _styles() -> dict[str, ParagraphStyle]:
    s: dict[str, ParagraphStyle] = {}

    def ps(name, **kw) -> ParagraphStyle:
        return ParagraphStyle(name, **kw)

    s["titulo"] = ps("titulo", fontSize=16, fontName="Helvetica-Bold",
                     textColor=BRANCO, leading=20)
    s["sec"]    = ps("sec",    fontSize=8,  fontName="Helvetica-Bold",
                     textColor=BRANCO, leading=10)
    s["label"]  = ps("label",  fontSize=7.5, fontName="Helvetica-Bold",
                     textColor=MUTED, leading=10)
    s["val"]    = ps("val",    fontSize=9,  fontName="Helvetica",
                     textColor=PRETO, leading=12)
    s["th"]     = ps("th",     fontSize=7.5, fontName="Helvetica-Bold",
                     textColor=MUTED, leading=9)
    s["td"]     = ps("td",     fontSize=8.5, fontName="Helvetica",
                     textColor=PRETO, leading=11)
    s["td_r"]   = ps("td_r",   fontSize=8.5, fontName="Helvetica",
                     textColor=PRETO, leading=11, alignment=TA_RIGHT)
    s["ttl_l"]  = ps("ttl_l",  fontSize=10, fontName="Helvetica-Bold",
                     textColor=BRANCO, leading=13)
    s["ttl_r"]  = ps("ttl_r",  fontSize=10, fontName="Helvetica-Bold",
                     textColor=BRANCO, leading=13, alignment=TA_RIGHT)
    s["obs"]    = ps("obs",    fontSize=8.5, fontName="Helvetica",
                     textColor=PRETO, leading=12)
    s["footer"] = ps("footer", fontSize=7.5, fontName="Helvetica",
                     textColor=MUTED, alignment=TA_CENTER, leading=10)
    s["val_r"]  = ps("val_r",  fontSize=9,  fontName="Helvetica",
                     textColor=PRETO, alignment=TA_RIGHT, leading=12)
    return s


# ── Helpers ─────────────────────────────────────────────────────────────────

def _brl(v: float) -> str:
    return "R$ {:,.2f}".format(v).replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_date(s: str) -> str:
    if not s:
        return "—"
    try:
        return datetime.date.fromisoformat(s).strftime("%d/%m/%Y")
    except ValueError:
        return s


def _sec_hdr(text: str, st: dict) -> Table:
    """Faixa de seção em verde."""
    t = Table([[Paragraph(text, st["sec"])]], colWidths=[17.6 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), VERDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ]))
    return t


def _kv(pairs: list[tuple[str, str]], st: dict) -> Table:
    """Mini-tabela label → valor."""
    rows = [[Paragraph(lbl, st["label"]), Paragraph(val or "—", st["val"])]
            for lbl, val in pairs]
    t = Table(rows, colWidths=[3.6 * cm, None])
    t.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# ── Builder principal ────────────────────────────────────────────────────────

def build_pdf(data: dict) -> bytes:
    """Gera o PDF e devolve os bytes. Recebe somente dados já validados."""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.2 * cm,  bottomMargin=1.5 * cm,
    )
    st    = _styles()
    story = []

    status_key  = data.get("status", "pendente")
    status_lbl  = _STATUS_LABEL.get(status_key, status_key.upper())
    status_fg   = _STATUS_FG.get(status_key, PRETO)
    status_bg   = _STATUS_BG.get(status_key, CINZA_CL)

    # ── CABEÇALHO ────────────────────────────────────────────────────────
    hdr = Table([[
        Paragraph("🧱  Material de Construção", st["titulo"]),
        Paragraph(
            f"<font size=8 color='#AABBA7'>Nº</font><br/>"
            f"<font size=14><b>{data.get('num_atend','—')}</b></font>",
            ParagraphStyle("nr", textColor=BRANCO, alignment=TA_RIGHT, leading=16),
        ),
    ]], colWidths=[12 * cm, 5.6 * cm])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), VERDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (0, -1),  14),
        ("RIGHTPADDING",  (-1, 0), (-1, -1), 14),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW",     (0, 0), (-1, 0),  3, TIJOLO),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 6))

    # ── RESUMO ────────────────────────────────────────────────────────────
    badge = Table([[Paragraph(
        f"  {status_lbl}  ",
        ParagraphStyle("b2", fontSize=8, fontName="Helvetica-Bold",
                       textColor=status_fg, leading=10),
    )]], colWidths=[2.8 * cm])
    badge.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), status_bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))

    resumo = Table([[
        Paragraph(f"<b>Tipo:</b> {data.get('tipo','—')}", st["val"]),
        Paragraph(
            f"<b>Data:</b> {_fmt_date(data.get('data',''))}  "
            f"<b>Hora:</b> {data.get('hora','—') or '—'}", st["val"]),
        Paragraph(f"<b>Atendente:</b> {data.get('vendedor','—') or '—'}", st["val"]),
        badge,
    ]], colWidths=[4.5 * cm, 5 * cm, 5.5 * cm, 2.6 * cm])
    resumo.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), CINZA_CL),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.5, CINZA_BD),
    ]))
    story.append(resumo)
    story.append(Spacer(1, 12))

    # ── CLIENTE ───────────────────────────────────────────────────────────
    story.append(_sec_hdr("▸  DADOS DO CLIENTE", st))
    story.append(Spacer(1, 6))

    cli = data.get("cliente", {})
    end = " ".join(filter(None, [cli.get("end"), cli.get("bairro"), cli.get("cidade")]))
    cli_left  = _kv([
        ("Nome / Razão Social", cli.get("nome", "—")),
        ("CPF / CNPJ",          cli.get("doc") or "—"),
        ("Endereço de Entrega", end or "—"),
    ], st)
    cli_right = _kv([
        ("Telefone",      cli.get("tel") or "—"),
        ("E-mail",        cli.get("email") or "—"),
        ("Obra / Projeto", cli.get("obra") or "—"),
    ], st)
    story.append(Table([[cli_left, cli_right]], colWidths=[9 * cm, 8.6 * cm]))
    story.append(Spacer(1, 12))

    # ── ITENS ─────────────────────────────────────────────────────────────
    story.append(_sec_hdr("▸  ITENS DO PEDIDO", st))
    story.append(Spacer(1, 6))

    thead = [
        Paragraph("#",                   st["th"]),
        Paragraph("DESCRIÇÃO",           st["th"]),
        Paragraph("CATEGORIA",           st["th"]),
        Paragraph("UN.",                 st["th"]),
        Paragraph("QTD.",                st["th"]),
        Paragraph("PREÇO UNIT.",         st["th"]),
        Paragraph("TOTAL",               st["th"]),
    ]
    rows = [thead]
    subtotal = 0.0

    for i, item in enumerate(data.get("itens", []), 1):
        total = float(item.get("total", 0))
        subtotal += total
        rows.append([
            Paragraph(str(i).zfill(2),                        st["td"]),
            Paragraph(str(item.get("desc") or "—"),            st["td"]),
            Paragraph(str(item.get("cat") or ""),              st["td"]),
            Paragraph(str(item.get("un") or ""),               st["td"]),
            Paragraph(str(item.get("qtd", 0)),                 st["td_r"]),
            Paragraph(_brl(float(item.get("preco", 0))),       st["td_r"]),
            Paragraph(_brl(total),                             st["td_r"]),
        ])

    itens_t = Table(rows,
        colWidths=[0.8*cm, 5.8*cm, 3.5*cm, 1.2*cm, 1.4*cm, 2.2*cm, 2.3*cm])

    cmds = [
        ("BACKGROUND",    (0, 0), (-1, 0),  CINZA_CL),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1), 0.4, CINZA_BD),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (4, 1), (-1, -1), "RIGHT"),
    ]
    for i in range(1, len(rows)):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), CINZA_CL))
    itens_t.setStyle(TableStyle(cmds))
    story.append(itens_t)

    # ── TOTAIS ────────────────────────────────────────────────────────────
    desc   = float(data.get("desconto", 0))
    frete  = float(data.get("frete", 0))
    v_desc = round(subtotal * desc / 100, 2)
    total  = round(subtotal - v_desc + frete, 2)

    sub_rows = [
        [Paragraph("Subtotal",                  st["label"]), Paragraph(_brl(subtotal),  st["val_r"])],
        [Paragraph(f"Desconto ({desc:.0f}%)",    st["label"]), Paragraph(f"- {_brl(v_desc)}", st["val_r"])],
        [Paragraph("Frete",                      st["label"]), Paragraph(_brl(frete),    st["val_r"])],
    ]
    sub_t = Table(sub_rows, colWidths=[3 * cm, 3 * cm])
    sub_t.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.4, CINZA_BD),
        ("ALIGN",         (1, 0), (1, -1),  "RIGHT"),
    ]))

    tot_row = Table([[
        Paragraph("TOTAL GERAL", st["ttl_l"]),
        Paragraph(_brl(total),   st["ttl_r"]),
    ]], colWidths=[3 * cm, 3 * cm])
    tot_row.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), VERDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (0, -1),  8),
        ("RIGHTPADDING",  (-1, 0), (-1, -1), 8),
    ]))

    right_blk = Table([[sub_t], [tot_row]])
    right_blk.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    outer = Table([[None, right_blk]], colWidths=[11.6 * cm, 6 * cm])
    outer.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(Spacer(1, 6))
    story.append(outer)
    story.append(Spacer(1, 12))

    # ── CONDIÇÕES ─────────────────────────────────────────────────────────
    story.append(_sec_hdr("▸  CONDIÇÕES COMERCIAIS", st))
    story.append(Spacer(1, 6))
    cond = Table([[
        _kv([("Pagamento",        data.get("pagamento", "—"))], st),
        _kv([("Prazo de Entrega", data.get("prazo") or "—")],   st),
        _kv([("Validade",         _fmt_date(data.get("validade", "")))], st),
    ]], colWidths=[6 * cm, 5 * cm, 6.6 * cm])
    cond.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(cond)
    story.append(Spacer(1, 12))

    # ── OBSERVAÇÕES ───────────────────────────────────────────────────────
    obs = (data.get("obs") or "").strip()
    if obs:
        story.append(_sec_hdr("▸  OBSERVAÇÕES", st))
        story.append(Spacer(1, 6))
        story.append(Paragraph(obs, st["obs"]))
        story.append(Spacer(1, 12))

    # ── ASSINATURAS ───────────────────────────────────────────────────────
    story.append(_sec_hdr("▸  ASSINATURAS", st))
    story.append(Spacer(1, 24))

    sig = Table(
        [["", ""], ["Atendente / Vendedor", "Cliente / Responsável"]],
        colWidths=[8.5 * cm, 8.5 * cm],
    )
    sig.setStyle(TableStyle([
        ("LINEABOVE",  (0, 0), (0, 0), 1, PRETO),
        ("LINEABOVE",  (1, 0), (1, 0), 1, PRETO),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME",   (0, 1), (-1, 1),  "Helvetica"),
        ("FONTSIZE",   (0, 1), (-1, 1),  8),
        ("TEXTCOLOR",  (0, 1), (-1, 1),  MUTED),
        ("TOPPADDING", (0, 1), (-1, 1),  4),
    ]))
    story.append(sig)
    story.append(Spacer(1, 20))

    # ── RODAPÉ ────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=CINZA_BD))
    story.append(Spacer(1, 4))
    now = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
    story.append(Paragraph(
        f"Documento gerado em {now}  •  Nº {data.get('num_atend','—')}  •  {status_lbl}",
        st["footer"],
    ))

    doc.build(story)
    return buf.getvalue()
