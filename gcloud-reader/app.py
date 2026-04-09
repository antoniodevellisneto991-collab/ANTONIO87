"""
Google Cloud Book Reader — Leitor de livros TXT com vozes neurais WaveNet/Neural2.
Usa os $300 de crédito grátis do Google Cloud (90 dias).
"""

import os
import io
import uuid
import base64
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google.cloud import texttospeech

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB

UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

# Google Cloud TTS client
_client = None


def get_client():
    global _client
    if _client is None:
        _client = texttospeech.TextToSpeechClient()
    return _client


# --- Neural Voices (WaveNet & Neural2) ---
VOICES = {
    # Português Brasil — WaveNet
    "pt-BR-Wavenet-A": {"label": "Francisca WaveNet (PT-BR) — Feminina, natural", "lang": "pt-BR", "gender": "FEMALE"},
    "pt-BR-Wavenet-B": {"label": "Roberto WaveNet (PT-BR) — Masculina, profunda", "lang": "pt-BR", "gender": "MALE"},
    "pt-BR-Wavenet-C": {"label": "Camila WaveNet (PT-BR) — Feminina, jovem", "lang": "pt-BR", "gender": "FEMALE"},
    # Português Brasil — Neural2 (melhor qualidade)
    "pt-BR-Neural2-A": {"label": "Ana Neural2 (PT-BR) — Feminina, premium", "lang": "pt-BR", "gender": "FEMALE"},
    "pt-BR-Neural2-B": {"label": "Lucas Neural2 (PT-BR) — Masculina, premium", "lang": "pt-BR", "gender": "MALE"},
    "pt-BR-Neural2-C": {"label": "Julia Neural2 (PT-BR) — Feminina, expressiva", "lang": "pt-BR", "gender": "FEMALE"},
    # Português Portugal
    "pt-PT-Wavenet-A": {"label": "Raquel WaveNet (PT-PT) — Feminina", "lang": "pt-PT", "gender": "FEMALE"},
    "pt-PT-Wavenet-B": {"label": "Duarte WaveNet (PT-PT) — Masculina", "lang": "pt-PT", "gender": "MALE"},
    "pt-PT-Wavenet-C": {"label": "Inês WaveNet (PT-PT) — Feminina, suave", "lang": "pt-PT", "gender": "FEMALE"},
    "pt-PT-Wavenet-D": {"label": "Miguel WaveNet (PT-PT) — Masculina, clara", "lang": "pt-PT", "gender": "MALE"},
    # English US
    "en-US-Neural2-C": {"label": "Aria Neural2 (EN-US) — Female, warm", "lang": "en-US", "gender": "FEMALE"},
    "en-US-Neural2-D": {"label": "James Neural2 (EN-US) — Male, deep", "lang": "en-US", "gender": "MALE"},
    "en-US-Neural2-F": {"label": "Emma Neural2 (EN-US) — Female, expressive", "lang": "en-US", "gender": "FEMALE"},
    # English UK
    "en-GB-Neural2-A": {"label": "Sonia Neural2 (EN-GB) — Female, British", "lang": "en-GB", "gender": "FEMALE"},
    "en-GB-Neural2-B": {"label": "Oliver Neural2 (EN-GB) — Male, British", "lang": "en-GB", "gender": "MALE"},
    # Spanish
    "es-ES-Neural2-A": {"label": "Elvira Neural2 (ES) — Femenina", "lang": "es-ES", "gender": "FEMALE"},
    "es-ES-Neural2-B": {"label": "Carlos Neural2 (ES) — Masculina", "lang": "es-ES", "gender": "MALE"},
    # French
    "fr-FR-Neural2-A": {"label": "Denise Neural2 (FR) — Féminine", "lang": "fr-FR", "gender": "FEMALE"},
    "fr-FR-Neural2-B": {"label": "Pierre Neural2 (FR) — Masculin", "lang": "fr-FR", "gender": "MALE"},
    # Italian
    "it-IT-Neural2-A": {"label": "Elsa Neural2 (IT) — Femminile", "lang": "it-IT", "gender": "FEMALE"},
    # German
    "de-DE-Neural2-A": {"label": "Katja Neural2 (DE) — Weiblich", "lang": "de-DE", "gender": "FEMALE"},
    "de-DE-Neural2-B": {"label": "Klaus Neural2 (DE) — Männlich", "lang": "de-DE", "gender": "MALE"},
    # Japanese
    "ja-JP-Neural2-B": {"label": "Nanami Neural2 (JA) — 女性", "lang": "ja-JP", "gender": "FEMALE"},
    "ja-JP-Neural2-C": {"label": "Keita Neural2 (JA) — 男性", "lang": "ja-JP", "gender": "MALE"},
}

# 5000 bytes is the API limit per request
TTS_CHAR_LIMIT = 5000
CHARS_PER_PAGE = 3000


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


def synthesize_speech(text: str, voice_name: str, speed: float = 1.0, pitch: float = 0.0) -> bytes:
    """Generate speech with Google Cloud TTS WaveNet/Neural2 voices."""
    client = get_client()
    voice_info = VOICES[voice_name]

    synthesis_input = texttospeech.SynthesisInput(text=text[:TTS_CHAR_LIMIT])

    voice = texttospeech.VoiceSelectionParams(
        language_code=voice_info["lang"],
        name=voice_name,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speed,
        pitch=pitch,
        effects_profile_id=["headphone-class-device"],
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    return response.audio_content


# --- Routes ---

@app.route("/")
def index():
    voices_for_template = {k: v["label"] for k, v in VOICES.items()}
    return render_template("index.html", voices=voices_for_template)


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
    voice = data.get("voice", "pt-BR-Neural2-A")
    speed = float(data.get("speed", 1.0))
    pitch = float(data.get("pitch", 0.0))

    if voice not in VOICES:
        return jsonify({"error": "Voz inválida"}), 400

    speed = max(0.5, min(2.0, speed))
    pitch = max(-10.0, min(10.0, pitch))

    try:
        audio = synthesize_speech(text, voice, speed, pitch)
        audio_b64 = base64.b64encode(audio).decode("utf-8")
        return jsonify({"audio": audio_b64, "format": "mp3"})
    except Exception as e:
        return jsonify({"error": f"Erro no TTS: {e}"}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "Google Cloud Book Reader — WaveNet/Neural2"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5002))
    app.run(debug=os.getenv("FLASK_ENV") == "development", host="0.0.0.0", port=port)
