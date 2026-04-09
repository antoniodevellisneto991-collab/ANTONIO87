package com.gemini.reader.data

/** Gemini TTS models. */
enum class TtsModel(val id: String, val label: String) {
    PRO("gemini-2.5-pro-tts", "Gemini 2.5 Pro TTS"),
    FLASH("gemini-2.5-flash-tts", "Gemini 2.5 Flash TTS"),
    FLASH_LITE("gemini-2.5-flash-lite-preview-tts", "Gemini 2.5 Flash Lite (Preview)"),
}

/** Gender for display only. */
enum class Gender { F, M }

/** One of the 30 Gemini TTS voices. */
data class Voice(val name: String, val gender: Gender)

val ALL_VOICES = listOf(
    Voice("Achernar", Gender.F),
    Voice("Achird", Gender.M),
    Voice("Algenib", Gender.M),
    Voice("Algieba", Gender.M),
    Voice("Alnilam", Gender.M),
    Voice("Aoede", Gender.F),
    Voice("Autonoe", Gender.F),
    Voice("Callirrhoe", Gender.F),
    Voice("Charon", Gender.M),
    Voice("Despina", Gender.F),
    Voice("Enceladus", Gender.M),
    Voice("Erinome", Gender.F),
    Voice("Fenrir", Gender.M),
    Voice("Gacrux", Gender.F),
    Voice("Iapetus", Gender.M),
    Voice("Kore", Gender.F),
    Voice("Laomedeia", Gender.F),
    Voice("Leda", Gender.F),
    Voice("Orus", Gender.M),
    Voice("Puck", Gender.M),
    Voice("Pulcherrima", Gender.F),
    Voice("Rasalgethi", Gender.M),
    Voice("Sadachbia", Gender.M),
    Voice("Sadaltager", Gender.M),
    Voice("Schedar", Gender.M),
    Voice("Sulafat", Gender.F),
    Voice("Umbriel", Gender.M),
    Voice("Vindemiatrix", Gender.F),
    Voice("Zephyr", Gender.F),
    Voice("Zubenelgenubi", Gender.M),
)

/** Style presets for reading. */
data class StylePreset(val id: String, val label: String, val prompt: String)

val STYLE_PRESETS = listOf(
    StylePreset("narrador", "Narrador", "Leia como um narrador profissional de audiobook, com tom calmo, pausas naturais e boa dicao."),
    StylePreset("dramatico", "Dramatico", "Leia de forma dramatica e expressiva, variando o tom conforme as emocoes do texto, como um ator de teatro."),
    StylePreset("suave", "Suave", "Leia de forma suave, tranquila e reconfortante, como se estivesse contando uma historia antes de dormir."),
    StylePreset("energetico", "Energetico", "Leia com energia e entusiasmo, mantendo o ouvinte engajado e interessado."),
    StylePreset("neutro", "Neutro", "Leia de forma neutra e clara, sem emocao exagerada, focando na clareza."),
    StylePreset("poetico", "Poetico", "Leia como um poeta, com cadencia ritmica, pausas artisticas e entonacao musical."),
    StylePreset("sussurro", "Sussurro", "[whispering] Leia em um sussurro suave e intimo, como se estivesse contando um segredo."),
    StylePreset("jornalistico", "Jornalistico", "Leia como um apresentador de noticias, com tom profissional e autoritativo."),
)

/** Supported languages (GA). */
data class Language(val code: String, val label: String)

val LANGUAGES = listOf(
    Language("pt-BR", "Portugues (Brasil)"),
    Language("pt-PT", "Portugues (Portugal)"),
    Language("en-US", "English (US)"),
    Language("en-GB", "English (UK)"),
    Language("en-IN", "English (India)"),
    Language("es-ES", "Espanol"),
    Language("es-MX", "Espanol (Mexico)"),
    Language("fr-FR", "Francais"),
    Language("de-DE", "Deutsch"),
    Language("it-IT", "Italiano"),
    Language("ja-JP", "Japanese"),
    Language("ko-KR", "Korean"),
    Language("cmn-CN", "Chinese (China)"),
    Language("ar-EG", "Arabic"),
    Language("hi-IN", "Hindi"),
    Language("ru-RU", "Russian"),
    Language("nl-NL", "Dutch"),
    Language("pl-PL", "Polish"),
    Language("tr-TR", "Turkish"),
    Language("id-ID", "Indonesian"),
    Language("vi-VN", "Vietnamese"),
    Language("th-TH", "Thai"),
    Language("uk-UA", "Ukrainian"),
    Language("ro-RO", "Romanian"),
    Language("sv-SE", "Swedish"),
)
