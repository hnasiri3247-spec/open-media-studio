import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'

def test_project_flow_and_render():
    r = client.post('/api/projects', json={"title":"test","script":"hello","format":"9:16","duration":1,"style":"cartoon"})
    assert r.status_code == 200
    pid = r.json()['id']
    r = client.post(f'/api/projects/{pid}/scenes', json={"prompt":"a cartoon character walks","duration":1})
    assert r.status_code == 200
    r = client.post(f'/api/projects/{pid}/voice', json={"text":"hello","voice":"default"})
    assert r.status_code == 200
    r = client.post(f'/api/projects/{pid}/render', json={"project_id":pid})
    assert r.status_code == 200
    r = client.get(f'/api/projects/{pid}/render/download')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('video/mp4')
