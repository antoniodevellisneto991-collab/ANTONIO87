# Gemini Book Reader — Android

App Android nativo para leitura de livros TXT com voz neural **Gemini 2.5 Flash TTS**.

## Funcionalidades

- Upload de arquivos .txt do celular
- 6 estilos de leitura: Narrador, Dramático, Suave, Energético, Neutro, Poético
- Modo automático (lê todas as páginas)
- Controle de tamanho de fonte
- Navegação por páginas
- Áudio via AudioTrack (PCM direto do Gemini)

## Como abrir no Android Studio

1. Abra o **Android Studio**
2. File → Open → selecione a pasta `android-gemini-reader`
3. Aguarde o Gradle sincronizar
4. A API key já está configurada no `build.gradle.kts`
5. Clique **Run** (ou Shift+F10)

## Alterar a API Key

Edite `app/build.gradle.kts`, linha:
```kotlin
buildConfigField("String", "GEMINI_API_KEY", "\"SUA_CHAVE_AQUI\"")
```

## Requisitos

- Android Studio Hedgehog ou superior
- Android SDK 35
- Dispositivo/emulador Android 8.0+ (API 26)
- Conexão com internet
