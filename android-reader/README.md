# Gemini Book Reader - Android

Leitor de livros TXT com Gemini TTS (Pro + Flash) para Android.

## Funcionalidades

- **Gemini 2.5 Pro TTS** + Flash TTS — modelos de voz de ultima geracao
- **30 vozes neurais** — Achernar, Aoede, Callirrhoe, Charon, Kore, etc.
- **25 idiomas** — pt-BR, en-US, es-ES, fr-FR, de-DE, ja-JP, ko-KR...
- **8 estilos de leitura** — Narrador, Dramatico, Suave, Sussurro, etc.
- **Multi-speaker** — suporte a multiplos locutores
- **Controle de estilo via prompt** — tom, emocao, ritmo, sotaque
- **Chunking automatico** — divide textos longos em blocos de 4000 bytes
- **Concatenacao de audio** — junta blocos em reproducao continua
- **Modo Auto** — le todas as paginas automaticamente

## Requisitos

- Android 8.0+ (API 26)
- Conta Google Cloud com Cloud Text-to-Speech API ativada
- Access Token (`gcloud auth print-access-token`)

## Build

```bash
# Abrir no Android Studio
# Ou build via CLI:
cd android-reader
./gradlew assembleDebug
```

## Como usar

1. Obtenha um access token:
   ```bash
   gcloud auth print-access-token
   ```
2. Abra o app e cole o token
3. Selecione um arquivo .txt
4. Escolha modelo (Pro/Flash), voz, estilo e idioma
5. Toque "Ouvir Pagina"

## Arquitetura

```
app/src/main/java/com/gemini/reader/
├── MainActivity.kt          # Entry point
├── ReaderApp.kt             # Application class
├── data/
│   ├── TtsConfig.kt         # Modelos, vozes, estilos, idiomas
│   └── BookParser.kt        # Parser TXT + chunking
├── tts/
│   └── CloudTtsService.kt   # Cloud TTS REST API client
└── ui/
    ├── Theme.kt             # Material 3 theme
    ├── ReaderViewModel.kt   # State management
    └── ReaderAppUi.kt       # Compose UI (upload, reader, player)
```

## API Limits

| Campo | Limite |
|-------|--------|
| Texto | 4.000 bytes |
| Prompt | 4.000 bytes |
| Audio saida | ~655 segundos |
