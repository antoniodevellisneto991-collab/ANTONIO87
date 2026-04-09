# Book Reader — Voz Neural Gratuita

Leitor de livros TXT com voz neural de alta qualidade, **100% gratuito**, usando Microsoft Edge TTS.

## Custo

**$0 — ZERO.** Sem API key, sem limites, sem cobrança. Leia quantos livros quiser.

## Funcionalidades

- **Upload de TXT** — Arraste e solte ou selecione
- **15 vozes neurais** — PT-BR, PT-PT, EN, ES, FR, IT, DE, JA
- **Modo automático** — Lê todas as páginas sequencialmente
- **Controle de velocidade** — 0.5x até 2.0x
- **Tema claro/escuro** — Detecção automática
- **Navegação por teclado** — Setas (páginas), Espaço (ouvir)
- **Barra de progresso** — Acompanhe o áudio em tempo real
- **Paginação inteligente** — Divide por parágrafos

## Vozes em Português

| Voz | Tipo |
|-----|------|
| Francisca (PT-BR) | Feminina, natural |
| Antonio (PT-BR) | Masculina, clara |
| Thalita (PT-BR) | Feminina, jovem |
| Raquel (PT-PT) | Feminina, suave |
| Duarte (PT-PT) | Masculina, profunda |

## Instalação

```bash
cd openai-reader
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Acesse: http://localhost:5001

## Requisitos

- Python 3.10+
- Conexão com internet (para o Edge TTS)
- **Nenhuma API key necessária**
