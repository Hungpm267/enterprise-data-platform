import pytest
from fastapi.testclient import TestClient
from src.web.app import app

client = TestClient(app)

def test_health_check_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_auth_and_protected_analytics_flow():
    # 1. Login as SMB Client
    login_res = client.post("/api/v1/auth/login", json={
        "email": "owner@olist-store.vn",
        "password": "client123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get User Profile
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "owner@olist-store.vn"
    assert me_res.json()["tenant_slug"] == "olist-retail"

    # 3. Access KPIs
    kpi_res = client.get("/api/v1/analytics/kpis", headers=headers)
    assert kpi_res.status_code == 200
    assert "total_revenue" in kpi_res.json()

    # 4. Access SCD 2 Explorer
    scd_res = client.get("/api/v1/explorer/scd2/orders", headers=headers)
    assert scd_res.status_code == 200
    assert isinstance(scd_res.json(), list)

def test_pipeline_trigger_rbac_protection():
    # 1. Login as SMB Client (Should be forbidden to trigger pipeline)
    client_login = client.post("/api/v1/auth/login", json={
        "email": "owner@olist-store.vn",
        "password": "client123"
    })
    client_token = client_login.json()["access_token"]
    forbidden_res = client.post(
        "/api/v1/pipelines/trigger",
        json={"connector": "postgres_db"},
        headers={"Authorization": f"Bearer {client_token}"}
    )
    assert forbidden_res.status_code == 403

    # 2. Login as Platform Super Admin (Should be allowed)
    admin_login = client.post("/api/v1/auth/login", json={
        "email": "admin@dashgrow.io",
        "password": "admin123"
    })
    admin_token = admin_login.json()["access_token"]
    allowed_res = client.post(
        "/api/v1/pipelines/trigger",
        json={"connector": "postgres_db"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert allowed_res.status_code == 200
