"""
Book Reader — Leitor de livros TXT com voz neural gratuita (Edge TTS / Microsoft).
Sem API key, sem custo, sem limite de caracteres.
"""

import os
import io
import uuid
import asyncio
import base64
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import edge_tts

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB

UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

# --- Neural Voices (Edge TTS) ---
VOICES = {
    # Português Brasil
    "pt-BR-FranciscaNeural": "Francisca (PT-BR) — Feminina, natural",
    "pt-BR-AntonioNeural": "Antonio (PT-BR) — Masculina, clara",
    "pt-BR-ThalitaNeural": "Thalita (PT-BR) — Feminina, jovem",
    # Português Portugal
    "pt-PT-RaquelNeural": "Raquel (PT-PT) — Feminina, suave",
    "pt-PT-DuarteNeural": "Duarte (PT-PT) — Masculina, profunda",
    # English
    "en-US-AriaNeural": "Aria (EN-US) — Female, expressive",
    "en-US-GuyNeural": "Guy (EN-US) — Male, warm",
    "en-US-JennyNeural": "Jenny (EN-US) — Female, friendly",
    "en-GB-SoniaNeural": "Sonia (EN-GB) — Female, British",
    # Spanish
    "es-ES-ElviraNeural": "Elvira (ES) — Femenina, cálida",
    "es-MX-DaliaNeural": "Dalia (ES-MX) — Femenina, mexicana",
    # French
    "fr-FR-DeniseNeural": "Denise (FR) — Féminine, douce",
    # Italian
    "it-IT-ElsaNeural": "Elsa (IT) — Femminile, chiara",
    # German
    "de-DE-KatjaNeural": "Katja (DE) — Weiblich, klar",
    # Japanese
    "ja-JP-NanamiNeural": "Nanami (JA) — 女性、自然",
}

CHARS_PER_PAGE = 3000

# Reuse event loop for edge_tts
_loop = None


def get_loop():
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop


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


async def _synthesize(text: str, voice: str, rate: str, pitch: str) -> bytes:
    """Generate speech with edge-tts."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    audio_data = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.write(chunk["data"])
    return audio_data.getvalue()


def synthesize_speech(text: str, voice: str, rate: str = "+0%", pitch: str = "+0Hz") -> bytes:
    """Sync wrapper for edge_tts async synthesis."""
    loop = get_loop()
    return loop.run_until_complete(_synthesize(text, voice, rate, pitch))


# --- Routes ---

@app.route("/")
def index():
    return render_template("index.html", voices=VOICES)


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
    voice = data.get("voice", "pt-BR-FranciscaNeural")
    rate = data.get("rate", "+0%")
    pitch = data.get("pitch", "+0Hz")

    if voice not in VOICES:
        return jsonify({"error": "Voz inválida"}), 400

    try:
        audio = synthesize_speech(text, voice, rate, pitch)
        if not audio:
            return jsonify({"error": "Falha ao gerar áudio"}), 500

        audio_b64 = base64.b64encode(audio).decode("utf-8")
        return jsonify({"audio": audio_b64, "format": "mp3"})
    except Exception as e:
        return jsonify({"error": f"Erro no TTS: {e}"}), 500


@app.route("/voices")
def list_voices():
    return jsonify(VOICES)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "Book Reader — Edge TTS (Gratuito)"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(debug=os.getenv("FLASK_ENV") == "development", host="0.0.0.0", port=port)
