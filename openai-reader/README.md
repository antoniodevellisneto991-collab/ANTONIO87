# OpenAI Book Reader

Leitor de livros TXT com voz neural da OpenAI.

## Funcionalidades

- **Upload de TXT** — Arraste e solte ou selecione arquivos de texto
- **Paginação automática** — Divide o texto em páginas por parágrafos
- **10 vozes neurais** — Alloy, Ash, Ballad, Coral, Echo, Fable, Nova, Onyx, Sage, Shimmer
- **2 modelos de qualidade** — HD (alta qualidade) e Standard (rápido)
- **Barra de progresso** — Acompanhe o áudio em tempo real
- **Tema claro/escuro** — Com detecção automática
- **Navegação por teclado** — Setas para páginas, Espaço para ouvir
- **Controle de fonte** — Ajuste de tamanho para leitura confortável

## Requisitos

- Python 3.10+
- Chave de API da OpenAI

## Instalação

```bash
cd openai-reader
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Editar .env com sua OPENAI_API_KEY
```

## Executar

```bash
python app.py
```

Acesse: http://localhost:5001

## Vozes Disponíveis

| Voz | Descrição |
|-----|-----------|
| Alloy | Neutra e equilibrada |
| Ash | Clara e confiante |
| Ballad | Suave e expressiva |
| Coral | Quente e amigável |
| Echo | Grave e profunda |
| Fable | Narrativa e envolvente |
| Nova | Jovem e energética |
| Onyx | Grave e autoritária |
| Sage | Calma e sábia |
| Shimmer | Leve e otimista |

## Modelos

- **tts-1-hd** — Alta qualidade, latência maior
- **tts-1** — Rápido, boa qualidade
