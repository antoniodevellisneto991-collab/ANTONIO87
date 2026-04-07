"""
OpenAI Book Reader — Leitor de livros TXT com voz neural OpenAI TTS.
"""

import os
import uuid
import base64
import math
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB

UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

# OpenAI client
client = None


def get_client() -> OpenAI:
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY não configurada")
        client = OpenAI(api_key=api_key)
    return client


# --- Voices ---
# OpenAI TTS voices (all neural): alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer
VOICES = {
    "alloy": "Alloy — Neutra e equilibrada",
    "ash": "Ash — Clara e confiante",
    "ballad": "Ballad — Suave e expressiva",
    "coral": "Coral — Quente e amigável",
    "echo": "Echo — Grave e profunda",
    "fable": "Fable — Narrativa e envolvente",
    "nova": "Nova — Jovem e energética",
    "onyx": "Onyx — Grave e autoritária",
    "sage": "Sage — Calma e sábia",
    "shimmer": "Shimmer — Leve e otimista",
}

# Max chars per TTS request (OpenAI limit is 4096)
TTS_CHAR_LIMIT = 4096

# Chars per "page" for reading
CHARS_PER_PAGE = 3000


def parse_txt(file_path: str) -> dict:
    """Parse a TXT file into pages for reading."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        full_text = f.read()

    full_text = full_text.strip()
    if not full_text:
        return {"pages": [], "total_pages": 0, "total_chars": 0}

    # Split into pages by paragraph boundaries near CHARS_PER_PAGE
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

    # If no paragraph breaks, split by character limit
    if not pages and full_text:
        for i in range(0, len(full_text), CHARS_PER_PAGE):
            chunk = full_text[i:i + CHARS_PER_PAGE]
            pages.append(chunk)

    return {
        "pages": pages,
        "total_pages": len(pages),
        "total_chars": len(full_text),
    }


def synthesize_speech(text: str, voice: str = "nova", model: str = "tts-1-hd") -> bytes:
    """Generate neural speech using OpenAI TTS API."""
    oai = get_client()

    # Truncate to API limit
    text = text[:TTS_CHAR_LIMIT]

    response = oai.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format="mp3",
    )

    return response.content


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
    voice = data.get("voice", "nova")
    model = data.get("model", "tts-1-hd")  # tts-1 (rápido) ou tts-1-hd (alta qualidade)

    if voice not in VOICES:
        return jsonify({"error": "Voz inválida"}), 400

    if model not in ("tts-1", "tts-1-hd"):
        return jsonify({"error": "Modelo inválido"}), 400

    try:
        audio = synthesize_speech(text, voice, model)
        audio_b64 = base64.b64encode(audio).decode("utf-8")
        return jsonify({"audio": audio_b64, "format": "mp3"})
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Erro no TTS: {e}"}), 500


@app.route("/health")
def health():
    has_key = bool(os.getenv("OPENAI_API_KEY"))
    return jsonify({"status": "ok", "openai_configured": has_key})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(debug=os.getenv("FLASK_ENV") == "development", host="0.0.0.0", port=port)
