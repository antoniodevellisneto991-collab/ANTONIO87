"""
Gemini Book Reader — Leitor de livros TXT com Gemini 2.5 Flash TTS.
Voz neural de última geração do Google, com instruções de estilo.
Usa os $300 de crédito grátis do Google Cloud.
"""

import os
import uuid
import base64
import wave
import io
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB

UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

CHARS_PER_PAGE = 3000

# Gemini client
_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            _client = genai.Client(api_key=api_key)
        else:
            # Fallback: usar Application Default Credentials (gcloud auth)
            _client = genai.Client(
                vertexai=True,
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "crucial-nuance-492615-a7"),
                location="us-central1",
            )
    return _client


# --- Style presets for literature reading ---
STYLES = {
    "narrador": "Leia como um narrador profissional de audiobook, com tom calmo, pausas naturais e boa dicção.",
    "dramatico": "Leia de forma dramática e expressiva, variando o tom conforme as emoções do texto, como um ator de teatro.",
    "suave": "Leia de forma suave, tranquila e reconfortante, como se estivesse contando uma história antes de dormir.",
    "energetico": "Leia com energia e entusiasmo, mantendo o ouvinte engajado e interessado.",
    "neutro": "Leia de forma neutra e clara, sem emoção exagerada, focando na clareza.",
    "poetico": "Leia como um poeta, com cadência rítmica, pausas artísticas e entonação musical.",
}

LANGUAGES = {
    "pt-BR": "Português (Brasil)",
    "pt-PT": "Português (Portugal)",
    "en-US": "English (US)",
    "en-GB": "English (UK)",
    "es-ES": "Español",
    "fr-FR": "Français",
    "de-DE": "Deutsch",
    "it-IT": "Italiano",
    "ja-JP": "日本語",
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


MODELS = {
    "pro": "gemini-2.5-pro-preview-tts",
    "flash": "gemini-2.5-flash-preview-tts",
}

# Gemini TTS voices
VOICE_OPTIONS = {
    "Kore": "Kore — Feminina, firme e clara",
    "Charon": "Charon — Masculina, profunda e quente",
    "Fenrir": "Fenrir — Masculina, expressiva",
    "Aoede": "Aoede — Feminina, suave e melódica",
    "Puck": "Puck — Masculina, jovem e energética",
    "Leda": "Leda — Feminina, natural e amigável",
    "Orus": "Orus — Masculina, grave e autoritária",
    "Zephyr": "Zephyr — Neutra, leve e clara",
}


def synthesize_speech(text: str, style: str = "narrador", language: str = "pt-BR", model: str = "pro", voice: str = "Kore") -> bytes:
    """Generate speech using Gemini 2.5 Pro/Flash TTS."""
    client = get_client()

    style_instruction = STYLES.get(style, STYLES["narrador"])
    lang_name = LANGUAGES.get(language, "Português (Brasil)")
    model_name = MODELS.get(model, MODELS["pro"])

    if voice not in VOICE_OPTIONS:
        voice = "Kore"

    response = client.models.generate_content(
        model=model_name,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice,
                    )
                ),
                language_code=language,
            ),
            system_instruction=style_instruction + f" Use o idioma {lang_name}.",
        ),
    )

    # Extract audio data
    audio_data = response.candidates[0].content.parts[0].inline_data.data

    # Convert raw PCM to WAV
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(24000)
        wf.writeframes(audio_data)

    return wav_buffer.getvalue()


# --- Routes ---

@app.route("/")
def index():
    return render_template("index.html", styles=STYLES, languages=LANGUAGES, voices=VOICE_OPTIONS, models=MODELS)


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    if not file.filename.lower().endswith(".txt"):
        return jsonify({"error": "Apenas arquivos .txt são suportados"}), 400

    file_id = str(uuid.uuid4())
    file_path = UPLOAD_FOLDER / f"{file_id}.txt"
    file.save(file_path)

    try:
        result = parse_txt(str(file_path))
        if result["total_pages"] == 0:
            return jsonify({"error": "O arquivo está vazio"}), 400

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
        return jsonify({"error": "Texto não fornecido"}), 400

    text = data["text"]
    style = data.get("style", "narrador")
    language = data.get("language", "pt-BR")
    model = data.get("model", "pro")
    voice = data.get("voice", "Kore")

    if style not in STYLES:
        return jsonify({"error": "Estilo inválido"}), 400

    try:
        audio = synthesize_speech(text, style, language, model, voice)
        audio_b64 = base64.b64encode(audio).decode("utf-8")
        return jsonify({"audio": audio_b64, "format": "wav"})
    except Exception as e:
        return jsonify({"error": f"Erro no TTS: {e}"}), 500


@app.route("/health")
def health():
    has_key = bool(os.getenv("GEMINI_API_KEY"))
    return jsonify({"status": "ok", "gemini_configured": has_key})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5003))
    app.run(debug=os.getenv("FLASK_ENV") == "development", host="0.0.0.0", port=port)
