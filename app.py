from flask import Flask, request, jsonify, send_from_directory, g, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_compress import Compress
from flasgger import Swagger
import requests
import uuid
import os
import time
import threading
import logging
import hashlib
from functools import wraps

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CORS aktivieren
CORS(app)

# Gzip-Komprimierung aktivieren
Compress(app)

# Swagger/OpenAPI Konfiguration
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"
}

swagger_template = {
    "info": {
        "title": "HTML to URL API",
        "description": "Ein Service zum Speichern von HTML-Code und Generieren von temporären URLs. Erstellt automatisch PDF-Versionen mit Gotenberg.",
        "version": "1.3.0",
        "contact": {
            "name": "API Support"
        }
    },
    "securityDefinitions": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Rate Limiting konfigurieren
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Verzeichnis für gespeicherte Dateien
HTML_DIR = "html_files"
os.makedirs(HTML_DIR, exist_ok=True)

# Basis-URL für die generierten Links (kann per Umgebungsvariable überschrieben werden)
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080")

# Maximales Alter der Dateien in Sekunden (24 Stunden)
MAX_FILE_AGE = int(os.environ.get("MAX_FILE_AGE", 24 * 60 * 60))

# Cleanup-Intervall in Sekunden (alle 10 Minuten prüfen)
CLEANUP_INTERVAL = int(os.environ.get("CLEANUP_INTERVAL", 10 * 60))

# Maximale Dateigröße in Bytes (Standard: 1MB)
MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 1 * 1024 * 1024))

# API-Key für Upload-Schutz (optional)
API_KEY = os.environ.get("API_KEY", None)

# Content Security Policy für ausgelieferte HTML-Dateien
CSP_POLICY = os.environ.get("CSP_POLICY", "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob: https:;")

# PDF-Generierung aktivieren/deaktivieren
PDF_ENABLED = os.environ.get("PDF_ENABLED", "true").lower() == "true"

# Gotenberg URL für PDF-Generierung
GOTENBERG_URL = os.environ.get("GOTENBERG_URL", "http://gotenberg:3000")


@app.before_request
def before_request():
    """Request-ID für jede Anfrage generieren."""
    # Prüfe ob Request-ID vom Proxy weitergeleitet wurde
    g.request_id = request.headers.get('X-Request-ID', uuid.uuid4().hex[:16])
    g.start_time = time.time()


@app.after_request
def after_request(response):
    """Request-ID und Timing zu Response hinzufügen."""
    # Request-ID Header
    response.headers['X-Request-ID'] = g.get('request_id', 'unknown')
    
    # Request-Dauer berechnen
    if hasattr(g, 'start_time'):
        duration = (time.time() - g.start_time) * 1000
        response.headers['X-Response-Time'] = f"{duration:.2f}ms"
    
    return response


def require_api_key(f):
    """Decorator für API-Key-Authentifizierung."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if API_KEY:
            provided_key = request.headers.get("X-API-Key")
            if not provided_key or provided_key != API_KEY:
                logger.warning(f"Ungültiger API-Key-Versuch von {get_remote_address()} (Request-ID: {g.get('request_id', 'unknown')})")
                return jsonify({"error": "Ungültiger oder fehlender API-Key"}), 401
        return f(*args, **kwargs)
    return decorated


def generate_pdf_with_gotenberg(html_content: str, pdf_path: str) -> bool:
    """Generiert eine PDF-Datei aus HTML-Content mit Gotenberg."""
    try:
        # Gotenberg Chromium HTML-zu-PDF Endpoint
        url = f"{GOTENBERG_URL}/forms/chromium/convert/html"
        
        # HTML als Datei senden
        files = {
            'files': ('index.html', html_content, 'text/html')
        }
        
        # PDF-Optionen
        data = {
            'marginTop': '1',
            'marginBottom': '1',
            'marginLeft': '1',
            'marginRight': '1',
            'printBackground': 'true'
        }
        
        response = requests.post(url, files=files, data=data, timeout=30)
        
        if response.status_code == 200:
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            return True
        else:
            logger.error(f"Gotenberg Fehler: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        logger.error("Gotenberg nicht erreichbar - läuft der Container?")
        return False
    except Exception as e:
        logger.error(f"PDF-Generierung fehlgeschlagen: {e}")
        return False


def cleanup_old_files():
    """Löscht Dateien, die älter als MAX_FILE_AGE sind."""
    while True:
        try:
            current_time = time.time()
            deleted_count = 0
            for filename in os.listdir(HTML_DIR):
                filepath = os.path.join(HTML_DIR, filename)
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getctime(filepath)
                    if file_age > MAX_FILE_AGE:
                        os.remove(filepath)
                        logger.info(f"Gelöscht: {filename} (Alter: {file_age/3600:.1f}h)")
                        deleted_count += 1
            if deleted_count > 0:
                logger.info(f"Cleanup abgeschlossen: {deleted_count} Datei(en) gelöscht")
        except Exception as e:
            logger.error(f"Fehler beim Cleanup: {e}")
        
        time.sleep(CLEANUP_INTERVAL)


# Starte Cleanup-Thread nur im Hauptprozess (für Gunicorn mit --preload)
_cleanup_started = False

def start_cleanup_thread():
    global _cleanup_started
    if not _cleanup_started:
        cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
        cleanup_thread.start()
        _cleanup_started = True
        logger.info("Cleanup-Thread gestartet")


@app.route("/upload", methods=["POST"])
@limiter.limit("30 per hour")
@require_api_key
def upload_html():
    """
    HTML-Code hochladen
    ---
    tags:
      - Upload
    security:
      - ApiKeyAuth: []
    consumes:
      - text/html
    parameters:
      - in: body
        name: body
        description: HTML-Code zum Speichern
        required: true
        schema:
          type: string
          example: "<!DOCTYPE html><html><body><h1>Hallo Welt!</h1></body></html>"
    responses:
      200:
        description: Upload erfolgreich
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            filename:
              type: string
              example: "a3f2c1b9e4d7.html"
            url:
              type: string
              example: "http://localhost:8080/files/a3f2c1b9e4d7.html"
            pdf_url:
              type: string
              example: "http://localhost:8080/files/a3f2c1b9e4d7.pdf"
      400:
        description: Kein HTML-Content im Request Body
      401:
        description: Ungültiger oder fehlender API-Key
      413:
        description: Datei zu groß
    """
    # Größenlimit prüfen
    if request.content_length and request.content_length > MAX_CONTENT_LENGTH:
        return jsonify({
            "error": f"Datei zu groß. Maximum: {MAX_CONTENT_LENGTH / 1024 / 1024:.1f}MB"
        }), 413
    
    html_content = request.get_data(as_text=True)
    
    if not html_content:
        return jsonify({"error": "Kein HTML-Content im Request Body gefunden"}), 400
    
    # Nochmal Größe des tatsächlichen Contents prüfen
    if len(html_content.encode('utf-8')) > MAX_CONTENT_LENGTH:
        return jsonify({
            "error": f"Datei zu groß. Maximum: {MAX_CONTENT_LENGTH / 1024 / 1024:.1f}MB"
        }), 413
    
    # Generiere UUID als Dateinamen (sicherer als Zufallszahlen)
    file_id = uuid.uuid4().hex[:12]
    html_filename = f"{file_id}.html"
    pdf_filename = f"{file_id}.pdf"
    html_filepath = os.path.join(HTML_DIR, html_filename)
    pdf_filepath = os.path.join(HTML_DIR, pdf_filename)
    
    # Falls die Datei bereits existiert (extrem unwahrscheinlich), generiere neue ID
    while os.path.exists(html_filepath):
        file_id = uuid.uuid4().hex[:12]
        html_filename = f"{file_id}.html"
        pdf_filename = f"{file_id}.pdf"
        html_filepath = os.path.join(HTML_DIR, html_filename)
        pdf_filepath = os.path.join(HTML_DIR, pdf_filename)
    
    # Speichere die HTML-Datei
    with open(html_filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    logger.info(f"Neue HTML-Datei erstellt: {html_filename} ({len(html_content)} Bytes) - Request-ID: {g.request_id}")
    
    # Generiere PDF-Version mit Gotenberg
    pdf_generated = False
    if PDF_ENABLED:
        pdf_generated = generate_pdf_with_gotenberg(html_content, pdf_filepath)
        if pdf_generated:
            pdf_size = os.path.getsize(pdf_filepath)
            logger.info(f"PDF erstellt: {pdf_filename} ({pdf_size} Bytes) - Request-ID: {g.request_id}")
        else:
            logger.warning(f"PDF-Generierung fehlgeschlagen für {file_id} - Request-ID: {g.request_id}")
    
    # Generiere die Links
    html_url = f"{BASE_URL}/files/{html_filename}"
    pdf_url = f"{BASE_URL}/files/{pdf_filename}" if pdf_generated else None
    
    response_data = {
        "success": True,
        "id": file_id,
        "filename": html_filename,
        "url": html_url
    }
    
    if PDF_ENABLED:
        response_data["pdf_filename"] = pdf_filename if pdf_generated else None
        response_data["pdf_url"] = pdf_url
        response_data["pdf_generated"] = pdf_generated
    
    return jsonify(response_data)


@app.route("/files/<filename>")
@limiter.limit("100 per minute")
def serve_file(filename):
    """
    HTML- oder PDF-Datei abrufen
    ---
    tags:
      - Files
    parameters:
      - name: filename
        in: path
        type: string
        required: true
        description: Dateiname (z.B. a3f2c1b9e4d7.html oder a3f2c1b9e4d7.pdf)
    responses:
      200:
        description: HTML- oder PDF-Datei
      400:
        description: Ungültiger Dateiname
      404:
        description: Datei nicht gefunden
    """
    # Sicherheitscheck: Nur .html und .pdf Dateien erlauben
    is_html = filename.endswith('.html')
    is_pdf = filename.endswith('.pdf')
    
    if (not is_html and not is_pdf) or '/' in filename or '\\' in filename:
        return jsonify({"error": "Ungültiger Dateiname"}), 400
    
    filepath = os.path.join(HTML_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Datei nicht gefunden"}), 404
    
    # Datei lesen für ETag-Berechnung
    with open(filepath, 'rb') as f:
        file_content = f.read()
    
    # ETag basierend auf Dateiinhalt
    etag = hashlib.md5(file_content).hexdigest()
    
    # Prüfe If-None-Match Header für Caching
    if request.headers.get('If-None-Match') == etag:
        return '', 304
    
    # MIME-Type bestimmen
    mimetype = 'text/html' if is_html else 'application/pdf'
    
    # Response erstellen
    response = make_response(send_from_directory(HTML_DIR, filename, mimetype=mimetype))
    
    # Cache-Header
    response.headers['ETag'] = etag
    response.headers['Cache-Control'] = 'public, max-age=3600'  # 1 Stunde
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # CSP und X-Frame-Options nur für HTML
    if is_html:
        response.headers['Content-Security-Policy'] = CSP_POLICY
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    # Content-Disposition für PDF (optional: Download erzwingen)
    if is_pdf:
        # inline = im Browser anzeigen, attachment = Download
        response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response


@app.route("/health")
@limiter.exempt
def health():
    """
    Health-Check
    ---
    tags:
      - System
    responses:
      200:
        description: Service ist gesund
        schema:
          type: object
          properties:
            status:
              type: string
              example: "healthy"
            pdf_enabled:
              type: boolean
              example: true
    """
    # Prüfe Gotenberg-Verbindung
    gotenberg_healthy = False
    if PDF_ENABLED:
        try:
            response = requests.get(f"{GOTENBERG_URL}/health", timeout=2)
            gotenberg_healthy = response.status_code == 200
        except:
            gotenberg_healthy = False
    
    return jsonify({
        "status": "healthy",
        "pdf_enabled": PDF_ENABLED,
        "gotenberg_connected": gotenberg_healthy if PDF_ENABLED else None
    })


@app.route("/stats")
@limiter.limit("10 per minute")
def stats():
    """
    Statistiken abrufen
    ---
    tags:
      - System
    responses:
      200:
        description: Statistiken über gespeicherte Dateien
        schema:
          type: object
          properties:
            total_files:
              type: integer
              example: 10
            html_files:
              type: integer
              example: 5
            pdf_files:
              type: integer
              example: 5
            total_size_mb:
              type: number
              example: 0.12
            pdf_enabled:
              type: boolean
              example: true
    """
    files = []
    current_time = time.time()
    total_size = 0
    html_count = 0
    pdf_count = 0
    
    for filename in os.listdir(HTML_DIR):
        filepath = os.path.join(HTML_DIR, filename)
        if os.path.isfile(filepath):
            file_age = current_time - os.path.getctime(filepath)
            file_size = os.path.getsize(filepath)
            remaining = MAX_FILE_AGE - file_age
            total_size += file_size
            
            file_type = "html" if filename.endswith('.html') else "pdf" if filename.endswith('.pdf') else "other"
            if file_type == "html":
                html_count += 1
            elif file_type == "pdf":
                pdf_count += 1
            
            files.append({
                "filename": filename,
                "type": file_type,
                "size_kb": round(file_size / 1024, 2),
                "age_hours": round(file_age / 3600, 2),
                "remaining_hours": round(max(0, remaining) / 3600, 2)
            })
    
    return jsonify({
        "total_files": len(files),
        "html_files": html_count,
        "pdf_files": pdf_count,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "max_age_hours": MAX_FILE_AGE / 3600,
        "max_file_size_mb": MAX_CONTENT_LENGTH / 1024 / 1024,
        "api_key_required": API_KEY is not None,
        "pdf_enabled": PDF_ENABLED,
        "files": files
    })


@app.route("/")
@limiter.exempt
def index():
    """
    API-Dokumentation
    ---
    tags:
      - System
    responses:
      200:
        description: API-Informationen und Dokumentation
        schema:
          type: object
          properties:
            service:
              type: string
              example: "HTML to URL"
            version:
              type: string
              example: "1.3.0"
            docs:
              type: string
              example: "/docs"
    """
    return jsonify({
        "service": "HTML to URL",
        "version": "1.3.0",
        "docs": f"{BASE_URL}/docs",
        "endpoints": {
            "POST /upload": "HTML-Code hochladen (Body: HTML) → HTML + PDF",
            "GET /files/<id>.html": "HTML-Datei abrufen",
            "GET /files/<id>.pdf": "PDF-Datei abrufen",
            "GET /health": "Health-Check",
            "GET /stats": "Statistiken",
            "GET /docs": "Swagger UI Dokumentation"
        },
        "config": {
            "max_file_size_mb": MAX_CONTENT_LENGTH / 1024 / 1024,
            "max_age_hours": MAX_FILE_AGE / 3600,
            "api_key_required": API_KEY is not None,
            "pdf_enabled": PDF_ENABLED
        }
    })


# Cleanup-Thread starten
start_cleanup_thread()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
