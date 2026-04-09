# Gemini Book Reader — Voz IA de Última Geração

Leitor de livros TXT usando **Gemini 2.5 Flash TTS** do Google.  
A voz mais avançada e natural disponível, com estilos de leitura personalizáveis.

## Diferencial

O Gemini 2.5 Flash TTS é superior ao Cloud TTS tradicional porque:
- Usa o modelo de linguagem Gemini para entender o **contexto** do texto
- Gera entonação e pausas **naturais** baseadas no conteúdo
- Suporta **instruções de estilo** (narrador, dramático, poético, etc.)

## Estilos de Leitura

| Estilo | Descrição |
|--------|-----------|
| Narrador | Tom calmo, pausas naturais, boa dicção |
| Dramático | Expressivo, varia tom conforme emoções |
| Suave | Tranquilo, como história antes de dormir |
| Energético | Entusiasta, mantém engajamento |
| Neutro | Claro, sem emoção exagerada |
| Poético | Cadência rítmica, pausas artísticas |

## Instalação

```bash
cd ~/Desktop/antonio87/gemini-reader
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env com sua GEMINI_API_KEY
python app.py
```

Acesse: http://127.0.0.1:5003

## Obter a API Key

1. Acesse https://console.cloud.google.com/vertex-ai/studio/media/speech
2. Clique **"Receber chave da API"**
3. Cole no `.env`
