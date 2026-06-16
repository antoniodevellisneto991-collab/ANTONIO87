#!/usr/bin/env bash
# Sobe a Book Quiz API localmente (macOS / Linux).
# Uso: ./run.sh
set -e

cd "$(dirname "$0")"

# 1. ambiente virtual
if [ ! -d ".venv" ]; then
  echo "==> Criando ambiente virtual (.venv)..."
  python3 -m venv .venv
fi
source .venv/bin/activate

# 2. dependências
echo "==> Instalando dependências..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 3. checar chave da OpenAI
if [ ! -f ".env" ]; then
  echo
  echo "!! Arquivo .env não encontrado."
  echo "   Crie um com sua chave:  echo 'OPENAI_API_KEY=sk-sua-chave' > .env"
  echo
  exit 1
fi

# 4. subir a API
echo "==> API em http://localhost:8000/docs  (Ctrl+C para parar)"
uvicorn main:app --reload
