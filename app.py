"""
Google Cloud Book Reader - Aplicação principal
Leitor de livros EPUB com Text-to-Speech (Google Cloud) e Cloud Storage.
"""

import os
import io
import uuid
import base64
from pathlib import Path

from flask import (
    Flask, render_template, request, jsonify,
    send_file, session
)
from dotenv import load_dotenv
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB max upload

UPLOAD_FOLDER = Path(__file__).parent / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

# --- Google Cloud clients (lazy init) ---

_tts_client = None
_storage_client = None


def get_tts_client():
    global _tts_client
    if _tts_client is None:
        from google.cloud import texttospeech
        _tts_client = texttospeech.TextToSpeechClient()
    return _tts_client


def get_storage_client():
    global _storage_client
    if _storage_client is None:
        from google.cloud import storage
        _storage_client = storage.Client()
    return _storage_client


# --- Helper functions ---

def extract_chapters_from_epub(file_path: str) -> list[dict]:
    """Extract chapters with title and HTML content from an EPUB file."""
    book = epub.read_epub(file_path, options={"ignore_ncx": True})
    chapters = []

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content().decode("utf-8", errors="replace")
        soup = BeautifulSoup(content, "lxml")

        # Extract text
        text = soup.get_text(separator="\n", strip=True)
        if not text or len(text) < 10:
            continue

        # Try to find chapter title
        title = None
        for tag in ["h1", "h2", "h3", "title"]:
            heading = soup.find(tag)
            if heading:
                title = heading.get_text(strip=True)
                break

        if not title:
            title = f"Capítulo {len(chapters) + 1}"

        # Clean HTML for reader display (keep basic formatting)
        for tag in soup.find_all(["script", "style", "meta", "link"]):
            tag.decompose()

        body = soup.find("body")
        html_content = str(body) if body else str(soup)

        chapters.append({
            "title": title,
            "text": text,
            "html": html_content,
        })

    return chapters


def get_epub_metadata(file_path: str) -> dict:
    """Extract metadata from an EPUB file."""
    book = epub.read_epub(file_path, options={"ignore_ncx": True})

    def get_meta(field):
        values = book.get_metadata("DC", field)
        return values[0][0] if values else None

    cover_b64 = None
    for item in book.get_items_of_type(ebooklib.ITEM_COVER):
        cover_b64 = base64.b64encode(item.get_content()).decode("utf-8")
        break

    if not cover_b64:
        for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
            name = item.get_name().lower()
            if "cover" in name:
                cover_b64 = base64.b64encode(item.get_content()).decode("utf-8")
                break

    return {
        "title": get_meta("title") or "Livro sem título",
        "author": get_meta("creator") or "Autor desconhecido",
        "language": get_meta("language") or "pt",
        "description": get_meta("description"),
        "cover": cover_b64,
    }


def synthesize_speech(text: str, language: str = "pt-BR") -> bytes | None:
    """Convert text to speech using Google Cloud Text-to-Speech."""
    try:
        from google.cloud import texttospeech
        client = get_tts_client()

        synthesis_input = texttospeech.SynthesisInput(text=text[:5000])
        voice = texttospeech.VoiceSelectionParams(
            language_code=language,
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.95,
        )
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        return response.audio_content
    except Exception:
        return None


def upload_to_gcs(file_path: str, destination_name: str) -> str | None:
    """Upload a file to Google Cloud Storage."""
    try:
        bucket_name = os.getenv("GCS_BUCKET_NAME")
        if not bucket_name:
            return None
        client = get_storage_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_name)
        blob.upload_from_filename(file_path)
        return blob.public_url
    except Exception:
        return None


# --- Routes ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext != ".epub":
        return jsonify({"error": "Formato não suportado. Envie um arquivo EPUB."}), 400

    file_id = str(uuid.uuid4())
    safe_name = f"{file_id}{ext}"
    file_path = UPLOAD_FOLDER / safe_name
    file.save(file_path)

    try:
        # Extract metadata and chapters
        metadata = get_epub_metadata(str(file_path))
        chapters = extract_chapters_from_epub(str(file_path))

        # Try uploading to GCS
        gcs_url = upload_to_gcs(str(file_path), f"books/{safe_name}")

        return jsonify({
            "id": file_id,
            "filename": file.filename,
            "metadata": metadata,
            "chapters": chapters,
            "total_chapters": len(chapters),
            "gcs_url": gcs_url,
        })
    except Exception as e:
        return jsonify({"error": f"Erro ao processar EPUB: {e}"}), 500
    finally:
        file_path.unlink(missing_ok=True)


@app.route("/tts", methods=["POST"])
def text_to_speech():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Texto não fornecido"}), 400

    text = data["text"]
    language = data.get("language", "pt-BR")
    audio = synthesize_speech(text, language)

    if audio is None:
        return jsonify({"error": "Text-to-Speech não disponível. Configure as credenciais do Google Cloud."}), 503

    audio_b64 = base64.b64encode(audio).decode("utf-8")
    return jsonify({"audio": audio_b64, "format": "mp3"})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "Google Cloud Book Reader"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(debug=os.getenv("FLASK_ENV") == "development", host="0.0.0.0", port=port)
