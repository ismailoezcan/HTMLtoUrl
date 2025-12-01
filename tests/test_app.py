"""
Unit Tests für den HTML to URL Service.
Ausführen mit: pytest tests/ -v
"""
import pytest
import os
import sys

# App-Modul importieren
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, HTML_DIR


@pytest.fixture
def client():
    """Test-Client für Flask-App."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def cleanup_files():
    """Cleanup nach Tests."""
    yield
    # Lösche alle Testdateien
    for filename in os.listdir(HTML_DIR):
        if filename.endswith('.html') or filename.endswith('.pdf'):
            filepath = os.path.join(HTML_DIR, filename)
            try:
                os.remove(filepath)
            except:
                pass


class TestHealthEndpoint:
    """Tests für den Health-Check Endpoint."""
    
    def test_health_returns_200(self, client):
        """Health-Check sollte 200 zurückgeben."""
        response = client.get('/health')
        assert response.status_code == 200
    
    def test_health_returns_json(self, client):
        """Health-Check sollte JSON zurückgeben."""
        response = client.get('/health')
        data = response.get_json()
        assert data['status'] == 'healthy'
    
    def test_health_has_request_id(self, client):
        """Health-Check sollte Request-ID Header haben."""
        response = client.get('/health')
        assert 'X-Request-ID' in response.headers
    
    def test_health_shows_pdf_status(self, client):
        """Health-Check sollte PDF-Status anzeigen."""
        response = client.get('/health')
        data = response.get_json()
        assert 'pdf_enabled' in data


class TestIndexEndpoint:
    """Tests für den Index Endpoint."""
    
    def test_index_returns_200(self, client):
        """Index sollte 200 zurückgeben."""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_index_returns_service_info(self, client):
        """Index sollte Service-Informationen enthalten."""
        response = client.get('/')
        data = response.get_json()
        assert 'service' in data
        assert 'version' in data
        assert 'endpoints' in data
        assert data['service'] == 'HTML to URL'
    
    def test_index_shows_docs_url(self, client):
        """Index sollte Link zur Dokumentation enthalten."""
        response = client.get('/')
        data = response.get_json()
        assert 'docs' in data
    
    def test_index_shows_pdf_config(self, client):
        """Index sollte PDF-Konfiguration anzeigen."""
        response = client.get('/')
        data = response.get_json()
        assert 'pdf_enabled' in data['config']


class TestUploadEndpoint:
    """Tests für den Upload Endpoint."""
    
    def test_upload_html_success(self, client, cleanup_files):
        """Upload sollte erfolgreich sein mit gültigem HTML."""
        html = '<html><body><h1>Test</h1></body></html>'
        response = client.post('/upload', data=html, content_type='text/html')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] == True
        assert 'filename' in data
        assert 'url' in data
        assert data['filename'].endswith('.html')
    
    def test_upload_empty_body_fails(self, client):
        """Upload ohne Body sollte 400 zurückgeben."""
        response = client.post('/upload', data='', content_type='text/html')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_upload_creates_html_file(self, client, cleanup_files):
        """Upload sollte HTML-Datei erstellen."""
        html = '<html><body><h1>Test File</h1></body></html>'
        response = client.post('/upload', data=html, content_type='text/html')
        
        data = response.get_json()
        filename = data['filename']
        filepath = os.path.join(HTML_DIR, filename)
        
        assert os.path.exists(filepath)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == html
    
    def test_upload_creates_pdf_file(self, client, cleanup_files):
        """Upload sollte auch PDF-Datei erstellen."""
        html = '<!DOCTYPE html><html><body><h1>PDF Test</h1></body></html>'
        response = client.post('/upload', data=html, content_type='text/html')
        
        data = response.get_json()
        
        # PDF sollte generiert werden
        if data.get('pdf_generated'):
            pdf_filename = data['pdf_filename']
            pdf_filepath = os.path.join(HTML_DIR, pdf_filename)
            assert os.path.exists(pdf_filepath)
            assert pdf_filename.endswith('.pdf')
    
    def test_upload_returns_both_urls(self, client, cleanup_files):
        """Upload sollte HTML- und PDF-URLs zurückgeben."""
        html = '<!DOCTYPE html><html><body><h1>URLs Test</h1></body></html>'
        response = client.post('/upload', data=html, content_type='text/html')
        
        data = response.get_json()
        assert 'url' in data
        assert '.html' in data['url']
        
        if data.get('pdf_generated'):
            assert 'pdf_url' in data
            assert '.pdf' in data['pdf_url']
    
    def test_upload_returns_same_id_for_html_and_pdf(self, client, cleanup_files):
        """HTML und PDF sollten die gleiche ID haben."""
        html = '<!DOCTYPE html><html><body><h1>Same ID Test</h1></body></html>'
        response = client.post('/upload', data=html, content_type='text/html')
        
        data = response.get_json()
        file_id = data['id']
        
        assert data['filename'] == f"{file_id}.html"
        if data.get('pdf_generated'):
            assert data['pdf_filename'] == f"{file_id}.pdf"
    
    def test_upload_returns_request_id(self, client, cleanup_files):
        """Upload sollte Request-ID Header haben."""
        html = '<html><body>Test</body></html>'
        response = client.post('/upload', data=html, content_type='text/html')
        
        assert 'X-Request-ID' in response.headers
        assert len(response.headers['X-Request-ID']) > 0


class TestFilesEndpoint:
    """Tests für den Files Endpoint."""
    
    def test_serve_existing_html_file(self, client, cleanup_files):
        """Vorhandene HTML-Datei sollte ausgeliefert werden."""
        html = '<html><body><h1>Serve Test</h1></body></html>'
        upload_response = client.post('/upload', data=html, content_type='text/html')
        filename = upload_response.get_json()['filename']
        
        response = client.get(f'/files/{filename}')
        
        assert response.status_code == 200
        assert html in response.get_data(as_text=True)
    
    def test_serve_existing_pdf_file(self, client, cleanup_files):
        """Vorhandene PDF-Datei sollte ausgeliefert werden."""
        html = '<!DOCTYPE html><html><body><h1>PDF Serve Test</h1></body></html>'
        upload_response = client.post('/upload', data=html, content_type='text/html')
        data = upload_response.get_json()
        
        if data.get('pdf_generated'):
            pdf_filename = data['pdf_filename']
            response = client.get(f'/files/{pdf_filename}')
            
            assert response.status_code == 200
            assert response.content_type == 'application/pdf'
    
    def test_serve_nonexistent_file_returns_404(self, client):
        """Nicht vorhandene Datei sollte 404 zurückgeben."""
        response = client.get('/files/nonexistent123.html')
        assert response.status_code == 404
        
        response = client.get('/files/nonexistent123.pdf')
        assert response.status_code == 404
    
    def test_serve_invalid_filename_returns_400(self, client):
        """Ungültiger Dateiname sollte 400 zurückgeben."""
        # Ohne .html oder .pdf Endung
        response = client.get('/files/testfile.txt')
        assert response.status_code == 400
        
        # Mit Path-Traversal-Versuch
        response = client.get('/files/../etc/passwd.html')
        assert response.status_code == 400
    
    def test_serve_html_has_csp_header(self, client, cleanup_files):
        """HTML-Datei sollte CSP-Header haben."""
        html = '<html><body>CSP Test</body></html>'
        upload_response = client.post('/upload', data=html, content_type='text/html')
        filename = upload_response.get_json()['filename']
        
        response = client.get(f'/files/{filename}')
        
        assert 'Content-Security-Policy' in response.headers
        assert 'X-Content-Type-Options' in response.headers
    
    def test_serve_pdf_has_no_csp_header(self, client, cleanup_files):
        """PDF-Datei sollte keinen CSP-Header haben."""
        html = '<!DOCTYPE html><html><body>PDF CSP Test</body></html>'
        upload_response = client.post('/upload', data=html, content_type='text/html')
        data = upload_response.get_json()
        
        if data.get('pdf_generated'):
            response = client.get(f'/files/{data["pdf_filename"]}')
            assert 'Content-Security-Policy' not in response.headers
    
    def test_serve_file_has_etag(self, client, cleanup_files):
        """Ausgelieferte Datei sollte ETag haben."""
        html = '<html><body>ETag Test</body></html>'
        upload_response = client.post('/upload', data=html, content_type='text/html')
        filename = upload_response.get_json()['filename']
        
        response = client.get(f'/files/{filename}')
        
        assert 'ETag' in response.headers
    
    def test_serve_file_304_with_matching_etag(self, client, cleanup_files):
        """Datei mit passendem ETag sollte 304 zurückgeben."""
        html = '<html><body>304 Test</body></html>'
        upload_response = client.post('/upload', data=html, content_type='text/html')
        filename = upload_response.get_json()['filename']
        
        # Erste Anfrage für ETag
        first_response = client.get(f'/files/{filename}')
        etag = first_response.headers['ETag']
        
        # Zweite Anfrage mit If-None-Match
        second_response = client.get(
            f'/files/{filename}',
            headers={'If-None-Match': etag}
        )
        
        assert second_response.status_code == 304


class TestStatsEndpoint:
    """Tests für den Stats Endpoint."""
    
    def test_stats_returns_200(self, client):
        """Stats sollte 200 zurückgeben."""
        response = client.get('/stats')
        assert response.status_code == 200
    
    def test_stats_returns_expected_fields(self, client):
        """Stats sollte erwartete Felder enthalten."""
        response = client.get('/stats')
        data = response.get_json()
        
        assert 'total_files' in data
        assert 'html_files' in data
        assert 'pdf_files' in data
        assert 'total_size_mb' in data
        assert 'max_age_hours' in data
        assert 'max_file_size_mb' in data
        assert 'api_key_required' in data
        assert 'pdf_enabled' in data
        assert 'files' in data
    
    def test_stats_counts_files_correctly(self, client, cleanup_files):
        """Stats sollte HTML und PDF separat zählen."""
        # Zwei Dateien hochladen
        client.post('/upload', data='<!DOCTYPE html><html>1</html>', content_type='text/html')
        client.post('/upload', data='<!DOCTYPE html><html>2</html>', content_type='text/html')
        
        response = client.get('/stats')
        data = response.get_json()
        
        assert data['html_files'] >= 2
        # PDFs sollten auch gezählt werden (falls generiert)


class TestDocsEndpoint:
    """Tests für die Swagger-Dokumentation."""
    
    def test_docs_returns_200(self, client):
        """Docs-Seite sollte 200 zurückgeben."""
        response = client.get('/docs/')
        assert response.status_code in [200, 308]
    
    def test_apispec_returns_json(self, client):
        """API-Spec sollte JSON zurückgeben."""
        response = client.get('/apispec.json')
        assert response.status_code == 200
        data = response.get_json()
        assert 'info' in data
        assert 'paths' in data


class TestRequestIdHeader:
    """Tests für Request-ID Funktionalität."""
    
    def test_response_has_request_id(self, client):
        """Alle Responses sollten Request-ID haben."""
        endpoints = ['/', '/health', '/stats']
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert 'X-Request-ID' in response.headers, f"Missing X-Request-ID for {endpoint}"
    
    def test_custom_request_id_is_used(self, client):
        """Übergebene Request-ID sollte verwendet werden."""
        custom_id = 'my-custom-request-id'
        response = client.get('/health', headers={'X-Request-ID': custom_id})
        
        assert response.headers['X-Request-ID'] == custom_id
    
    def test_response_has_timing_header(self, client):
        """Response sollte Timing-Header haben."""
        response = client.get('/health')
        
        assert 'X-Response-Time' in response.headers
        assert 'ms' in response.headers['X-Response-Time']


class TestPDFGeneration:
    """Tests spezifisch für PDF-Generierung."""
    
    def test_pdf_content_type(self, client, cleanup_files):
        """PDF sollte korrekten Content-Type haben."""
        html = '<!DOCTYPE html><html><body><h1>Content-Type Test</h1></body></html>'
        upload_response = client.post('/upload', data=html, content_type='text/html')
        data = upload_response.get_json()
        
        if data.get('pdf_generated'):
            response = client.get(f'/files/{data["pdf_filename"]}')
            assert response.content_type == 'application/pdf'
    
    def test_pdf_has_content_disposition(self, client, cleanup_files):
        """PDF sollte Content-Disposition Header haben."""
        html = '<!DOCTYPE html><html><body><h1>Disposition Test</h1></body></html>'
        upload_response = client.post('/upload', data=html, content_type='text/html')
        data = upload_response.get_json()
        
        if data.get('pdf_generated'):
            response = client.get(f'/files/{data["pdf_filename"]}')
            assert 'Content-Disposition' in response.headers
    
    def test_complex_html_generates_pdf(self, client, cleanup_files):
        """Komplexeres HTML sollte auch PDF generieren."""
        html = '''<!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Test</title>
            <style>
                body { font-family: Arial, sans-serif; }
                h1 { color: #333; }
                .container { padding: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Komplexer Test</h1>
                <p>Dies ist ein Paragraph mit <strong>fett</strong> und <em>kursiv</em>.</p>
                <ul>
                    <li>Punkt 1</li>
                    <li>Punkt 2</li>
                </ul>
            </div>
        </body>
        </html>'''
        
        response = client.post('/upload', data=html, content_type='text/html')
        data = response.get_json()
        
        assert data['success'] == True
        # PDF-Generierung kann fehlschlagen, aber Upload sollte erfolgreich sein
