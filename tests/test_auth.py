from fastapi.testclient import TestClient

from data_analyst_agent.api.app import create_app


def test_register_then_use_token_on_protected_endpoint(patched_data_source):
    app = create_app()
    with TestClient(app) as client:
        register_resp = client.post(
            "/api/v1/auth/register",
            json={"email": "alice@example.com", "password": "correct-horse"},
        )
        assert register_resp.status_code == 201
        token = register_resp.json()["access_token"]

        schema_resp = client.get(
            "/api/v1/dataset/schema", headers={"Authorization": f"Bearer {token}"}
        )
        assert schema_resp.status_code == 200
        assert schema_resp.json()["table_name"] == "purchases"


def test_duplicate_registration_is_rejected(patched_data_source):
    app = create_app()
    with TestClient(app) as client:
        payload = {"email": "bob@example.com", "password": "correct-horse"}
        first = client.post("/api/v1/auth/register", json=payload)
        second = client.post("/api/v1/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 400


def test_login_with_correct_and_wrong_password(patched_data_source):
    app = create_app()
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/register",
            json={"email": "carol@example.com", "password": "correct-horse"},
        )

        good = client.post(
            "/api/v1/auth/login",
            json={"email": "carol@example.com", "password": "correct-horse"},
        )
        bad = client.post(
            "/api/v1/auth/login",
            json={"email": "carol@example.com", "password": "wrong-password"},
        )

    assert good.status_code == 200
    assert "access_token" in good.json()
    assert bad.status_code == 401


def test_protected_endpoint_rejects_garbage_token(patched_data_source):
    app = create_app()
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/dataset/schema", headers={"Authorization": "Bearer not-a-real-token"}
        )

    assert response.status_code == 401
