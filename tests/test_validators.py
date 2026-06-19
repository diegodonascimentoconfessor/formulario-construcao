"""
tests/test_validators.py
Testes unitários do validador sem necessidade de subir o servidor.
Execute com:  python -m pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.validators.atendimento import validate_atendimento

BASE = {
    "num_atend": "ATD-2025-001",
    "tipo": "Orçamento",
    "data": "2025-06-18",
    "hora": "09:00",
    "vendedor": "João",
    "status": "pendente",
    "cliente": {"nome": "Maria Silva", "doc": "111.222.333-44"},
    "itens": [{"desc": "Cimento CP-II", "cat": "Cimento e Argamassa",
               "un": "sc", "qtd": 10, "preco": 35.00}],
    "desconto": 5,
    "frete": 50,
    "pagamento": "PIX",
    "prazo": "3 dias úteis",
    "validade": "2025-07-01",
    "obs": "Entrega pela manhã.",
}


def test_payload_valido():
    r = validate_atendimento(BASE)
    assert r.ok, r.errors
    assert r.data["cliente"]["nome"] == "Maria Silva"
    assert r.data["itens"][0]["total"] == 350.00


def test_num_atend_obrigatorio():
    bad = {**BASE, "num_atend": ""}
    r = validate_atendimento(bad)
    assert not r.ok
    assert any("num_atend" in e for e in r.errors)


def test_tipo_invalido():
    bad = {**BASE, "tipo": "Tipo Inexistente"}
    r = validate_atendimento(bad)
    assert not r.ok


def test_status_invalido():
    bad = {**BASE, "status": "suspenso"}
    r = validate_atendimento(bad)
    assert not r.ok


def test_desconto_acima_100():
    bad = {**BASE, "desconto": 150}
    r = validate_atendimento(bad)
    assert not r.ok


def test_xss_sanitizado():
    inj = {**BASE, "obs": "<script>alert('xss')</script>Observação normal"}
    r = validate_atendimento(inj)
    assert r.ok
    assert "<script>" not in r.data["obs"]
    assert "Observação normal" in r.data["obs"]


def test_preco_negativo():
    bad_itens = [{**BASE["itens"][0], "preco": -10}]
    bad = {**BASE, "itens": bad_itens}
    r = validate_atendimento(bad)
    assert not r.ok


def test_data_invalida():
    bad = {**BASE, "data": "18/06/2025"}   # formato errado
    r = validate_atendimento(bad)
    assert not r.ok


def test_sem_cliente_nome():
    bad = {**BASE, "cliente": {"nome": "", "doc": ""}}
    r = validate_atendimento(bad)
    assert not r.ok


def test_total_calculado_corretamente():
    r = validate_atendimento(BASE)
    assert r.ok
    item = r.data["itens"][0]
    assert item["total"] == item["qtd"] * item["preco"]


if __name__ == "__main__":
    tests = [fn for name, fn in list(globals().items()) if name.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passou(ram)  |  {failed} falhou(aram)")
