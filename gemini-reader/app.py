"""
Gemini Book Reader — Leitor de livros TXT com Gemini TTS (Pro + Flash).
Vozes neurais de ultima geracao com controle de estilo via prompts.
Suporta locutor unico e multiplos locutores.
"""

import os
import uuid
import base64
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google.cloud import texttospeech_v1beta1 as texttospeech
from google.api_core.client_options import ClientOptions

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB

UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

CHARS_PER_PAGE = 3000

# --- Cloud TTS client (lazy init) ---

_client = None


def get_client():
    global _client
    if _client is None:
        location = os.getenv("TTS_LOCATION", "global")
        api_endpoint = (
            f"{location}-texttospeech.googleapis.com"
            if location != "global"
            else "texttospeech.googleapis.com"
        )
        _client = texttospeech.TextToSpeechClient(
            client_options=ClientOptions(api_endpoint=api_endpoint)
        )
    return _client


# --- Models ---
MODELS = {
    "gemini-2.5-pro-tts": "Gemini 2.5 Pro TTS — Audiobooks, podcasts, qualidade maxima",
    "gemini-2.5-flash-tts": "Gemini 2.5 Flash TTS — Baixa latencia, multi-speaker",
    "gemini-2.5-flash-lite-preview-tts": "Gemini 2.5 Flash Lite TTS — Ultra rapido, economico (preview)",
}

# --- 30 Gemini TTS Voices ---
VOICES = {
    "Achernar": {"gender": "Feminino", "label": "Achernar — Feminino"},
    "Achird": {"gender": "Masculino", "label": "Achird — Masculino"},
    "Algenib": {"gender": "Masculino", "label": "Algenib — Masculino"},
    "Algieba": {"gender": "Masculino", "label": "Algieba — Masculino"},
    "Alnilam": {"gender": "Masculino", "label": "Alnilam — Masculino"},
    "Aoede": {"gender": "Feminino", "label": "Aoede — Feminino"},
    "Autonoe": {"gender": "Feminino", "label": "Autonoe — Feminino"},
    "Callirrhoe": {"gender": "Feminino", "label": "Callirrhoe — Feminino"},
    "Charon": {"gender": "Masculino", "label": "Charon — Masculino"},
    "Despina": {"gender": "Feminino", "label": "Despina — Feminino"},
    "Enceladus": {"gender": "Masculino", "label": "Enceladus — Masculino"},
    "Erinome": {"gender": "Feminino", "label": "Erinome — Feminino"},
    "Fenrir": {"gender": "Masculino", "label": "Fenrir — Masculino"},
    "Gacrux": {"gender": "Feminino", "label": "Gacrux — Feminino"},
    "Iapetus": {"gender": "Masculino", "label": "Iapetus — Masculino"},
    "Kore": {"gender": "Feminino", "label": "Kore — Feminino"},
    "Laomedeia": {"gender": "Feminino", "label": "Laomedeia — Feminino"},
    "Leda": {"gender": "Feminino", "label": "Leda — Feminino"},
    "Orus": {"gender": "Masculino", "label": "Orus — Masculino"},
    "Puck": {"gender": "Masculino", "label": "Puck — Masculino"},
    "Pulcherrima": {"gender": "Feminino", "label": "Pulcherrima — Feminino"},
    "Rasalgethi": {"gender": "Masculino", "label": "Rasalgethi — Masculino"},
    "Sadachbia": {"gender": "Masculino", "label": "Sadachbia — Masculino"},
    "Sadaltager": {"gender": "Masculino", "label": "Sadaltager — Masculino"},
    "Schedar": {"gender": "Masculino", "label": "Schedar — Masculino"},
    "Sulafat": {"gender": "Feminino", "label": "Sulafat — Feminino"},
    "Umbriel": {"gender": "Masculino", "label": "Umbriel — Masculino"},
    "Vindemiatrix": {"gender": "Feminino", "label": "Vindemiatrix — Feminino"},
    "Zephyr": {"gender": "Feminino", "label": "Zephyr — Feminino"},
    "Zubenelgenubi": {"gender": "Masculino", "label": "Zubenelgenubi — Masculino"},
}

# --- Style presets ---
STYLES = {
    "narrador": "Leia como um narrador profissional de audiobook, com tom calmo, pausas naturais e boa dicao.",
    "dramatico": "Leia de forma dramatica e expressiva, variando o tom conforme as emocoes do texto, como um ator de teatro.",
    "suave": "Leia de forma suave, tranquila e reconfortante, como se estivesse contando uma historia antes de dormir.",
    "energetico": "Leia com energia e entusiasmo, mantendo o ouvinte engajado e interessado.",
    "neutro": "Leia de forma neutra e clara, sem emocao exagerada, focando na clareza.",
    "poetico": "Leia como um poeta, com cadencia ritmica, pausas artisticas e entonacao musical.",
    "sarcastico": "Leia com tom sarcastico e ironico, como se nao levasse o texto a serio.",
    "sussurro": "Leia em um sussurro suave e intimo, como se estivesse contando um segredo.",
    "jornalistico": "Leia como um apresentador de noticias, com tom profissional e autoritativo.",
}

# --- Languages (GA + Preview) ---
LANGUAGES = {
    "pt-BR": "Portugues (Brasil)",
    "pt-PT": "Portugues (Portugal)",
    "en-US": "English (US)",
    "en-GB": "English (UK)",
    "en-IN": "English (India)",
    "en-AU": "English (Australia)",
    "es-ES": "Espanol (Espana)",
    "es-MX": "Espanol (Mexico)",
    "fr-FR": "Francais (France)",
    "fr-CA": "Francais (Canada)",
    "de-DE": "Deutsch",
    "it-IT": "Italiano",
    "ja-JP": "Japanese",
    "ko-KR": "Korean",
    "cmn-CN": "Chinese Mandarin (China)",
    "cmn-TW": "Chinese Mandarin (Taiwan)",
    "ar-EG": "Arabic (Egypt)",
    "hi-IN": "Hindi",
    "ru-RU": "Russian",
    "nl-NL": "Dutch",
    "pl-PL": "Polish",
    "tr-TR": "Turkish",
    "th-TH": "Thai",
    "vi-VN": "Vietnamese",
    "id-ID": "Indonesian",
    "sv-SE": "Swedish",
    "da-DK": "Danish",
    "nb-NO": "Norwegian",
    "fi-FI": "Finnish",
    "el-GR": "Greek",
    "he-IL": "Hebrew",
    "uk-UA": "Ukrainian",
    "ro-RO": "Romanian",
    "hu-HU": "Hungarian",
    "cs-CZ": "Czech",
    "bg-BG": "Bulgarian",
    "sk-SK": "Slovak",
    "sr-RS": "Serbian",
    "hr-HR": "Croatian",
    "bn-BD": "Bengali",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "mr-IN": "Marathi",
    "sw-KE": "Swahili",
}


def parse_txt(file_path: str) -> dict:
    """Parse a TXT file into pages splitting by paragraphs."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        full_text = f.read()

    full_text = full_text.strip()
    if not full_text:
        return {"pages": [], "total_pages": 0, "total_chars": 0}

    pages = []
    paragraphs = full_text.split("\n\n")
    current_page = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_page) + len(para) + 2 > CHARS_PER_PAGE and current_page:
            pages.append(current_page.strip())
            current_page = para
        else:
            current_page += "\n\n" + para if current_page else para

    if current_page.strip():
        pages.append(current_page.strip())

    if not pages and full_text:
        for i in range(0, len(full_text), CHARS_PER_PAGE):
            pages.append(full_text[i:i + CHARS_PER_PAGE])

    return {
        "pages": pages,
        "total_pages": len(pages),
        "total_chars": len(full_text),
    }


def synthesize_speech(
    text: str,
    style: str = "narrador",
    language: str = "pt-BR",
    voice_name: str = "Kore",
    model: str = "gemini-2.5-pro-tts",
    audio_format: str = "MP3",
) -> bytes:
    """Generate speech using Gemini TTS via Cloud Text-to-Speech API."""
    client = get_client()

    style_instruction = STYLES.get(style, STYLES["narrador"])

    synthesis_input = texttospeech.SynthesisInput(
        text=text[:4000],
        prompt=style_instruction,
    )

    voice = texttospeech.VoiceSelectionParams(
        language_code=language,
        name=voice_name,
        model_name=model,
    )

    encoding = getattr(
        texttospeech.AudioEncoding, audio_format, texttospeech.AudioEncoding.MP3
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=encoding,
        sample_rate_hertz=24000,
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    return response.audio_content


def synthesize_multispeaker(
    text: str,
    style: str = "narrador",
    language: str = "pt-BR",
    speakers: list[dict] | None = None,
    model: str = "gemini-2.5-pro-tts",
) -> bytes:
    """Generate multi-speaker speech using Gemini TTS.

    Args:
        text: Dialog text with "SpeakerAlias: line" format.
        speakers: List of {"alias": "Name", "voice": "VoiceName"} dicts.
    """
    client = get_client()

    style_instruction = STYLES.get(style, STYLES["narrador"])

    if not speakers or len(speakers) < 2:
        speakers = [
            {"alias": "Speaker1", "voice": "Kore"},
            {"alias": "Speaker2", "voice": "Charon"},
        ]

    speaker_configs = [
        texttospeech.MultispeakerPrebuiltVoice(
            speaker_alias=s["alias"],
            speaker_id=s["voice"],
        )
        for s in speakers
    ]

    multi_speaker_voice_config = texttospeech.MultiSpeakerVoiceConfig(
        speaker_voice_configs=speaker_configs
    )

    synthesis_input = texttospeech.SynthesisInput(
        text=text[:4000],
        prompt=style_instruction,
    )

    voice = texttospeech.VoiceSelectionParams(
        language_code=language,
        model_name=model,
        multi_speaker_voice_config=multi_speaker_voice_config,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        sample_rate_hertz=24000,
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    return response.audio_content


# --- Routes ---

@app.route("/")
def index():
    return render_template(
        "index.html",
        styles=STYLES,
        languages=LANGUAGES,
        voices=VOICES,
        models=MODELS,
    )


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    if not file.filename.lower().endswith(".txt"):
        return jsonify({"error": "Apenas arquivos .txt sao suportados"}), 400

    file_id = str(uuid.uuid4())
    file_path = UPLOAD_FOLDER / f"{file_id}.txt"
    file.save(file_path)

    try:
        result = parse_txt(str(file_path))
        if result["total_pages"] == 0:
            return jsonify({"error": "O arquivo esta vazio"}), 400

        return jsonify({
            "id": file_id,
            "filename": file.filename,
            **result,
        })
    finally:
        file_path.unlink(missing_ok=True)


@app.route("/tts", methods=["POST"])
def text_to_speech():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Texto nao fornecido"}), 400

    text = data["text"]
    style = data.get("style", "narrador")
    language = data.get("language", "pt-BR")
    voice_name = data.get("voice", "Kore")
    model = data.get("model", "gemini-2.5-pro-tts")

    if style not in STYLES:
        return jsonify({"error": "Estilo invalido"}), 400
    if voice_name not in VOICES:
        return jsonify({"error": "Voz invalida"}), 400
    if model not in MODELS:
        return jsonify({"error": "Modelo invalido"}), 400

    try:
        audio = synthesize_speech(text, style, language, voice_name, model)
        audio_b64 = base64.b64encode(audio).decode("utf-8")
        return jsonify({"audio": audio_b64, "format": "mp3"})
    except Exception as e:
        return jsonify({"error": f"Erro no TTS: {e}"}), 500


@app.route("/tts/multispeaker", methods=["POST"])
def text_to_speech_multispeaker():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Texto nao fornecido"}), 400

    text = data["text"]
    style = data.get("style", "narrador")
    language = data.get("language", "pt-BR")
    model = data.get("model", "gemini-2.5-pro-tts")
    speakers = data.get("speakers")

    if style not in STYLES:
        return jsonify({"error": "Estilo invalido"}), 400
    if model not in MODELS:
        return jsonify({"error": "Modelo invalido"}), 400

    try:
        audio = synthesize_multispeaker(text, style, language, speakers, model)
        audio_b64 = base64.b64encode(audio).decode("utf-8")
        return jsonify({"audio": audio_b64, "format": "mp3"})
    except Exception as e:
        return jsonify({"error": f"Erro no TTS multi-speaker: {e}"}), 500


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "Gemini Book Reader — Pro + Flash TTS",
        "models": list(MODELS.keys()),
        "voices": len(VOICES),
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5003))
    app.run(debug=os.getenv("FLASK_ENV") == "development", host="0.0.0.0", port=port)
