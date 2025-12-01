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
        if filename.endswith('.html'):
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
    
    def test_upload_creates_file(self, client, cleanup_files):
        """Upload sollte Datei erstellen."""
        html = '<html><body><h1>Test File</h1></body></html>'
        response = client.post('/upload', data=html, content_type='text/html')
        
        data = response.get_json()
        filename = data['filename']
        filepath = os.path.join(HTML_DIR, filename)
        
        assert os.path.exists(filepath)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == html
    
    def test_upload_returns_request_id(self, client, cleanup_files):
        """Upload sollte Request-ID Header haben."""
        html = '<html><body>Test</body></html>'
        response = client.post('/upload', data=html, content_type='text/html')
        
        assert 'X-Request-ID' in response.headers
        assert len(response.headers['X-Request-ID']) > 0


class TestFilesEndpoint:
    """Tests für den Files Endpoint."""
    
    def test_serve_existing_file(self, client, cleanup_files):
        """Vorhandene Datei sollte ausgeliefert werden."""
        # Erst hochladen
        html = '<html><body><h1>Serve Test</h1></body></html>'
        upload_response = client.post('/upload', data=html, content_type='text/html')
        filename = upload_response.get_json()['filename']
        
        # Dann abrufen
        response = client.get(f'/files/{filename}')
        
        assert response.status_code == 200
        assert html in response.get_data(as_text=True)
    
    def test_serve_nonexistent_file_returns_404(self, client):
        """Nicht vorhandene Datei sollte 404 zurückgeben."""
        response = client.get('/files/nonexistent123.html')
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    def test_serve_invalid_filename_returns_400(self, client):
        """Ungültiger Dateiname sollte 400 zurückgeben."""
        # Ohne .html Endung
        response = client.get('/files/testfile.txt')
        assert response.status_code == 400
        
        # Mit Path-Traversal-Versuch
        response = client.get('/files/../etc/passwd.html')
        assert response.status_code == 400
    
    def test_serve_file_has_csp_header(self, client, cleanup_files):
        """Ausgelieferte Datei sollte CSP-Header haben."""
        html = '<html><body>CSP Test</body></html>'
        upload_response = client.post('/upload', data=html, content_type='text/html')
        filename = upload_response.get_json()['filename']
        
        response = client.get(f'/files/{filename}')
        
        assert 'Content-Security-Policy' in response.headers
        assert 'X-Content-Type-Options' in response.headers
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
    
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
        assert 'total_size_mb' in data
        assert 'max_age_hours' in data
        assert 'max_file_size_mb' in data
        assert 'api_key_required' in data
        assert 'files' in data
    
    def test_stats_counts_files(self, client, cleanup_files):
        """Stats sollte Dateien korrekt zählen."""
        # Zwei Dateien hochladen
        client.post('/upload', data='<html>1</html>', content_type='text/html')
        client.post('/upload', data='<html>2</html>', content_type='text/html')
        
        response = client.get('/stats')
        data = response.get_json()
        
        assert data['total_files'] >= 2


class TestDocsEndpoint:
    """Tests für die Swagger-Dokumentation."""
    
    def test_docs_returns_200(self, client):
        """Docs-Seite sollte 200 zurückgeben."""
        response = client.get('/docs/')
        # Swagger UI kann 200 oder 308 (Redirect) zurückgeben
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

