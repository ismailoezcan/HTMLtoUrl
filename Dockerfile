FROM python:3.12-slim

WORKDIR /app

# curl für Healthcheck installieren
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root User erstellen
RUN useradd -m -u 1000 appuser

# Abhängigkeiten installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Anwendungscode kopieren
COPY app.py .

# Verzeichnis für HTML-Dateien erstellen und Rechte setzen
RUN mkdir -p html_files && chown -R appuser:appuser /app

# Zu non-root User wechseln
USER appuser

# Port freigeben
EXPOSE 8080

# Health-Check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Anwendung mit Gunicorn starten (--preload für korrekten Cleanup-Thread)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--preload", "app:app"]
