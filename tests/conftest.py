"""Shared pytest fixtures: fresh migrated DB per test + FastAPI TestClient."""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from stratos.app import App
from stratos.api.app import create_app


@pytest.fixture()
def stratos(tmp_path):
    return App(str(tmp_path / "test.db"))


@pytest.fixture()
def client(stratos):
    api = create_app(stratos)
    with TestClient(api) as c:
        yield c


@pytest.fixture()
def owner(client):
    """Register a starter-plan tenant; returns (headers, body)."""
    r = client.post("/auth/register", json={
        "email": "owner@duka.co.ke", "password": "passw0rd123",
        "tenant_name": "Test Duka", "phone": "0712345678"})
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    return {"Authorization": f"Bearer {tok}"}, r.json()


@pytest.fixture()
def pro_headers(client):
    """A pro-plan tenant (all six modules entitled)."""
    r = client.post("/auth/register", json={
        "email": "boss@bigco.co.ke", "password": "passw0rd123",
        "tenant_name": "Big Co", "plan_id": "pro"})
    tok = r.json()["token"]
    return {"Authorization": f"Bearer {tok}"}
