# HTML to URL Service

Ein sicherer Docker-Container, der HTML-Code entgegennimmt, als temporäre Datei speichert und **automatisch eine PDF-Version erstellt**.

## Features

- 📄 **Automatische PDF-Generierung** aus HTML
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
| `POST` | `/upload` | HTML-Code hochladen → HTML + PDF |
| `GET` | `/files/<id>.html` | HTML-Datei abrufen |
| `GET` | `/files/<id>.pdf` | PDF-Datei abrufen |
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

### HTML hochladen

```bash
curl -X POST http://localhost:8080/upload \
  -H "Content-Type: text/html" \
  -d '<!DOCTYPE html><html><body><h1>Hallo Welt!</h1></body></html>'
```

**Antwort:**
```json
{
  "success": true,
  "id": "a3f2c1b9e4d7",
  "filename": "a3f2c1b9e4d7.html",
  "url": "http://localhost:8080/files/a3f2c1b9e4d7.html",
  "pdf_filename": "a3f2c1b9e4d7.pdf",
  "pdf_url": "http://localhost:8080/files/a3f2c1b9e4d7.pdf",
  "pdf_generated": true
}
```

### Mit API-Key

```bash
curl -X POST http://localhost:8080/upload \
  -H "Content-Type: text/html" \
  -H "X-API-Key: mein-geheimer-schluessel" \
  -d '<!DOCTYPE html><html><body><h1>Hallo Welt!</h1></body></html>'
```

### HTML-Datei abrufen

```bash
curl http://localhost:8080/files/a3f2c1b9e4d7.html
```

### PDF-Datei abrufen

```bash
# Im Browser öffnen oder herunterladen
curl -O http://localhost:8080/files/a3f2c1b9e4d7.pdf
```

### Statistiken abrufen

```bash
curl http://localhost:8080/stats
```

**Antwort:**
```json
{
  "total_files": 10,
  "html_files": 5,
  "pdf_files": 5,
  "total_size_mb": 0.25,
  "max_age_hours": 24,
  "max_file_size_mb": 1.0,
  "api_key_required": false,
  "pdf_enabled": true,
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
| `PDF_ENABLED` | PDF-Generierung aktivieren | `true` |
| `GOTENBERG_URL` | URL zum Gotenberg-Service | `http://gotenberg:3000` |

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
| `ETag` | Cache-Validierung |
| `Content-Security-Policy` | Sicherheits-Policy (nur HTML) |
| `Content-Disposition` | Dateiname (nur PDF) |

## PDF-Generierung

Die PDF-Generierung erfolgt mit **[Gotenberg](https://gotenberg.dev/)** – einem Docker-Service der Chromium für perfekte HTML-zu-PDF Konvertierung nutzt.

### Vorteile von Gotenberg

- ✅ **Chromium-basiert** – identisches Rendering wie im Browser
- ✅ **CSS3 & JavaScript** vollständig unterstützt
- ✅ **Web-Fonts** (Google Fonts, etc.)
- ✅ **Responsive Layouts** werden korrekt gerendert
- ✅ **Bilder** (inline, base64, externe URLs)
- ✅ **Tabellen, Flexbox, Grid**
- ✅ **Print-Stylesheets** (`@media print`)

### Tipps für bessere PDFs

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    @page {
      size: A4;
      margin: 2cm;
    }
    @media print {
      .no-print { display: none; }
    }
    body {
      font-family: Arial, sans-serif;
      font-size: 12pt;
      line-height: 1.5;
    }
  </style>
</head>
<body>
  <h1>Mein Dokument</h1>
  <p>Inhalt hier...</p>
</body>
</html>
```

### PDF deaktivieren

Falls keine PDFs benötigt werden:

```bash
PDF_ENABLED=false docker-compose up -d
```

### Gotenberg separat nutzen

Gotenberg läuft als separater Container und kann auch direkt angesprochen werden:

```bash
# Gotenberg-Port freigeben (in docker-compose.yml)
# ports:
#   - "3000:3000"

# Direkt konvertieren
curl -X POST http://localhost:3000/forms/chromium/convert/html \
  -F files=@index.html -o output.pdf
```

## Persistenz

Um die Dateien dauerhaft zu speichern, verwende ein Volume:

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

## CI/CD & GitHub Packages

Das Projekt enthält eine GitHub Actions Workflow-Datei (`.github/workflows/ci.yml`), die bei jedem Push auf `main`:

1. **Tests ausführt** mit pytest
2. **Docker Image baut** 
3. **Push zu GitHub Container Registry** (ghcr.io)

### Image von GitHub Packages verwenden

```bash
# Login (einmalig, mit GitHub Personal Access Token)
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Image pullen (ersetze OWNER/REPO mit deinem Repository)
docker pull ghcr.io/OWNER/REPO:latest

# Mit docker-compose (docker-compose.ghcr.yml)
docker-compose -f docker-compose.ghcr.yml up -d
```

### Verfügbare Tags

| Tag | Beschreibung |
|-----|--------------|
| `latest` | Neuester Stand von main |
| `main` | Branch-Name |
| `abc123f` | Commit-SHA (kurz) |

## Reverse Proxy (Produktion)

Für den Produktionseinsatz mit HTTPS wird ein Reverse Proxy empfohlen. Eine Beispiel-Konfiguration für Nginx findest du in `nginx/nginx.conf`.

```bash
# Certbot für SSL-Zertifikate
sudo certbot --nginx -d example.com
```

## Lokale Entwicklung

```bash
# Gotenberg für PDF-Generierung starten
docker run -d -p 3000:3000 --name gotenberg gotenberg/gotenberg:8

# Virtuelle Umgebung erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt

# Server starten (mit Gotenberg-URL)
GOTENBERG_URL=http://localhost:3000 python app.py

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

## Changelog

### v1.3.0
- ✨ Automatische PDF-Generierung mit WeasyPrint
- 📁 Gleiche ID für HTML und PDF (`<id>.html` / `<id>.pdf`)
- ⚙️ `PDF_ENABLED` Umgebungsvariable

### v1.2.0
- 📚 Swagger UI Dokumentation
- 🏷️ Request-ID und Response-Time Headers
- ⚡ ETag Caching
- 🛡️ Content Security Policy

### v1.1.0
- 🔐 API-Key-Authentifizierung
- 🚦 Rate Limiting
- 📦 Gzip-Komprimierung
- 🌐 CORS-Support
