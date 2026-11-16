import os
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.infrastructure.workspace.ROOT", tmp_path)
    with TestClient(app) as application_client:
        yield application_client


@pytest.fixture
def loaded(client):
    filename = os.environ.get("F1_TEST_SAVE")
    if not filename:
        pytest.skip("Defina F1_TEST_SAVE para executar os testes com um save real.")
    original = Path(filename).read_bytes()
    response = client.post("/api/saves", files={"file": ("save5.sav", original)})
    assert response.status_code == 201, response.text
    return response.json()["id"], original
