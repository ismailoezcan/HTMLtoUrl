# HTML to URL Service

Ein sicherer Docker-Container, der HTML-Code entgegennimmt und als temporäre Datei speichert.

## Features

- 🔐 **API-Key-Authentifizierung** (optional)
- 🚦 **Rate Limiting** zum Schutz vor Missbrauch
- 📦 **Gzip-Komprimierung** für schnellere Responses
- 🌐 **CORS-Support** für Cross-Origin-Anfragen
- 🧹 **Automatische Löschung** nach 24 Stunden
- 🔒 **Non-Root Container** für erhöhte Sicherheit
- ❤️ **Health-Checks** für Container-Orchestrierung
- 📚 **Swagger UI** Dokumentation unter `/docs`
- 🏷️ **Request-ID Tracking** für Debugging
- 🛡️ **Content Security Policy** für ausgelieferte Dateien
- ⚡ **ETag Caching** für bessere Performance

## Endpoints

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| `GET` | `/` | API-Dokumentation |
| `GET` | `/docs` | Swagger UI |
| `POST` | `/upload` | HTML-Code hochladen |
| `GET` | `/files/<filename>` | HTML-Datei abrufen |
| `GET` | `/health` | Health-Check |
| `GET` | `/stats` | Statistiken |

## Schnellstart

### Mit Docker Compose (empfohlen)

```bash
# Starten
docker-compose up -d

# Mit API-Key (in .env Datei oder direkt)
API_KEY=geheim docker-compose up -d

# Logs anzeigen
docker-compose logs -f

# Stoppen
docker-compose down
```

### Mit Docker

```bash
# Image bauen
docker build -t html-to-url .

# Container starten (einfach)
docker run -d -p 8080:8080 --name html-to-url html-to-url

# Container mit API-Key-Schutz
docker run -d -p 8080:8080 \
  -e API_KEY=mein-geheimer-schluessel \
  --name html-to-url html-to-url

# Produktions-Setup (mit allen Optionen)
docker run -d -p 8080:8080 \
  -e BASE_URL=https://example.com \
  -e API_KEY=mein-geheimer-schluessel \
  -e MAX_FILE_AGE=43200 \
  -e MAX_CONTENT_LENGTH=2097152 \
  -v html_data:/app/html_files \
  --name html-to-url html-to-url
```

## Verwendung

### HTML hochladen (ohne API-Key)

```bash
curl -X POST http://localhost:8080/upload \
  -H "Content-Type: text/html" \
  -d '<!DOCTYPE html><html><body><h1>Hallo Welt!</h1></body></html>'
```

### HTML hochladen (mit API-Key)

```bash
curl -X POST http://localhost:8080/upload \
  -H "Content-Type: text/html" \
  -H "X-API-Key: mein-geheimer-schluessel" \
  -d '<!DOCTYPE html><html><body><h1>Hallo Welt!</h1></body></html>'
```

**Antwort:**
```json
{
  "success": true,
  "filename": "a3f2c1b9e4d7.html",
  "url": "http://localhost:8080/files/a3f2c1b9e4d7.html"
}
```

### HTML-Datei abrufen

Öffne einfach die zurückgegebene URL im Browser oder mit curl:

```bash
curl http://localhost:8080/files/a3f2c1b9e4d7.html
```

### Statistiken abrufen

```bash
curl http://localhost:8080/stats
```

**Antwort:**
```json
{
  "total_files": 5,
  "total_size_mb": 0.12,
  "max_age_hours": 24,
  "max_file_size_mb": 1.0,
  "api_key_required": true,
  "files": [...]
}
```

### API-Dokumentation

Öffne im Browser: `http://localhost:8080/docs`

## Umgebungsvariablen

| Variable | Beschreibung | Standard |
|----------|--------------|----------|
| `BASE_URL` | Basis-URL für generierte Links | `http://localhost:8080` |
| `API_KEY` | API-Key für Upload-Schutz (leer = deaktiviert) | - |
| `MAX_FILE_AGE` | Maximales Dateialter in Sekunden | `86400` (24h) |
| `MAX_CONTENT_LENGTH` | Maximale Dateigröße in Bytes | `1048576` (1MB) |
| `CLEANUP_INTERVAL` | Cleanup-Prüfintervall in Sekunden | `600` (10min) |
| `CSP_POLICY` | Content Security Policy für HTML-Dateien | `default-src 'self' ...` |

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `POST /upload` | 30 pro Stunde |
| `GET /files/*` | 100 pro Minute |
| `GET /stats` | 10 pro Minute |
| `GET /health` | Unbegrenzt |
| `GET /docs` | Unbegrenzt |
| Global | 200 pro Tag, 50 pro Stunde |

## Response Headers

Jede Response enthält hilfreiche Headers:

| Header | Beschreibung |
|--------|--------------|
| `X-Request-ID` | Eindeutige ID für Debugging |
| `X-Response-Time` | Bearbeitungszeit in ms |
| `ETag` | Cache-Validierung (nur `/files/*`) |
| `Content-Security-Policy` | Sicherheits-Policy (nur `/files/*`) |

## Persistenz

Um die HTML-Dateien dauerhaft zu speichern, verwende ein Volume:

```bash
docker run -d -p 8080:8080 \
  -v html_data:/app/html_files \
  --name html-to-url html-to-url
```

## Sicherheit

- **UUID-basierte Dateinamen**: Nicht erratbar (12 Zeichen hex)
- **Dateigrößen-Limit**: Schutz vor Speicher-Flooding
- **Rate Limiting**: Schutz vor API-Missbrauch
- **API-Key**: Optionaler Schutz für Uploads
- **Non-Root Container**: Minimale Berechtigungen
- **Path Traversal Protection**: Sichere Dateinamen-Validierung
- **Content Security Policy**: Schutz vor XSS in HTML-Dateien
- **Security Headers**: X-Content-Type-Options, X-Frame-Options

## Tests

```bash
# Virtuelle Umgebung erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt

# Tests ausführen
pytest tests/ -v

# Mit Coverage-Report
pytest tests/ -v --cov=app --cov-report=html
```

## CI/CD

Das Projekt enthält eine GitHub Actions Workflow-Datei (`.github/workflows/ci.yml`), die bei jedem Push:

1. **Tests ausführt** mit pytest
2. **Docker Image baut** und testet
3. Optional: **Push zu Docker Hub** (Secrets erforderlich)

## Reverse Proxy (Produktion)

Für den Produktionseinsatz mit HTTPS wird ein Reverse Proxy empfohlen. Eine Beispiel-Konfiguration für Nginx findest du in `nginx/nginx.conf`.

```bash
# Certbot für SSL-Zertifikate
sudo certbot --nginx -d example.com
```

## Lokale Entwicklung

```bash
# Virtuelle Umgebung erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt

# Server starten
python app.py

# Server läuft auf http://localhost:8080
```

## Projektstruktur

```
.
├── app.py                 # Hauptanwendung
├── requirements.txt       # Python Dependencies
├── Dockerfile            # Container-Definition
├── docker-compose.yml    # Docker Compose Setup
├── pytest.ini            # Pytest-Konfiguration
├── .gitignore
├── .dockerignore
├── nginx/
│   └── nginx.conf        # Nginx Reverse Proxy Beispiel
├── .github/
│   └── workflows/
│       └── ci.yml        # GitHub Actions CI/CD
└── tests/
    ├── __init__.py
    └── test_app.py       # Unit Tests
```
