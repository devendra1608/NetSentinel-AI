from fastapi.testclient import TestClient
from backend.app.main import app


client = TestClient(app)

def test_health_endpoints_returns_ok() -> None:
  response = client.get("/health")

  assert response.status_code == 200
  assert response.json() == {
    "status": "ok",
    "service": "NetSentinel-AI",
  }

def test_openapi_documentation_is_available() -> None:
  response = client.get("/openapi.json")

  assert response.status_code == 200
  assert response.json()["info"]["title"] == "NetSentinel-AI"

  