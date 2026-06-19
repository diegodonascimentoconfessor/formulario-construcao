"""
run.py — ponto de entrada da aplicação.
Execute com:  python run.py
"""
from app import create_app

app = create_app()

# Vercel importa o 'app' diretamente — o bloco abaixo só roda local
if __name__ == "__main__":
    app.run(debug=True, port=5000)
