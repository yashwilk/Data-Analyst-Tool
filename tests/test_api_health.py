from fastapi.testclient import TestClient

from data_analyst_agent.api.app import create_app


def test_health_endpoint_returns_ok(patched_data_source):
    # /health itself touches neither DB nor dataset, but app startup
    # (lifespan) always loads the dataset schema -- patched here so this
    # test doesn't require a live Supabase connection.
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dataset_schema_requires_auth(patched_data_source):
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/dataset/schema")

    assert response.status_code == 401
