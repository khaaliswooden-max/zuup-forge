"""Auto-generated tests for Aureon™."""

import pytest
from fastapi.testclient import TestClient

from platforms.aureon.app import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ready():
    resp = client.get("/ready")
    assert resp.status_code == 200

def test_get_opportunities():
    resp = client.get("/api/v1/opportunities")
    assert resp.status_code in (200, 401, 404)

def test_get_opportunities_id():
    resp = client.get("/api/v1/opportunities/test-id")
    assert resp.status_code in (200, 401, 404)

def test_get_opportunities_id_matches():
    resp = client.get("/api/v1/opportunities/test-id/matches")
    assert resp.status_code in (200, 401, 404)

def test_get_vendors():
    resp = client.get("/api/v1/vendors")
    assert resp.status_code in (200, 401, 404)

def test_get_vendors_id():
    resp = client.get("/api/v1/vendors/test-id")
    assert resp.status_code in (200, 401, 404)
