# Formulário de Atendimento — Material de Construção

## Estrutura

```
construcao/
├── run.py                      ← ponto de entrada
├── config.py                   ← configurações por ambiente
├── requirements.txt
├── .env.example
├── app/
│   ├── __init__.py             ← factory create_app()
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main.py             ← GET /
│   │   └── pdf.py              ← POST /gerar_pdf
│   ├── services/
│   │   ├── __init__.py
│   │   └── pdf_service.py      ← lógica de geração PDF
│   ├── validators/
│   │   ├── __init__.py
│   │   └── atendimento.py      ← validação/sanitização do payload
│   └── utils/
│       ├── __init__.py
│       └── security.py         ← helpers de segurança
├── logs/                       ← gerado em runtime
└── tests/
    └── test_validators.py
```

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env
python run.py
```
