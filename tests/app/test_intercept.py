import os
import sys

import pytest

APP_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "app")
sys.path.insert(0, os.path.abspath(APP_DIR))

from intercept import validate_target  # noqa: E402

from app import ACTIVITY_LOG, app  # type: ignore[attr-defined] # noqa: E402


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_health(client):
    response = client.get("/intercept/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


@pytest.mark.parametrize(
    "target",
    ["", "javascript:alert(1)", "ftp://example.com", "https://", "https://" + "a" * 3000 + ".com"],
)
def test_invalid_targets_are_rejected(target):
    assert validate_target(target) != ""


def test_valid_target_accepted():
    assert validate_target("https://example.com/path?q=1") == ""


def test_intercept_renders_analysis(client):
    response = client.get("/intercept", query_string={"target": "https://example.com/login"})
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "https://example.com/login" in body
    assert "continueBtn" in body


def test_intercept_rejects_bad_scheme(client):
    response = client.get("/intercept", query_string={"target": "javascript:alert(1)"})
    assert response.status_code == 400
    assert "continueBtn" not in response.get_data(as_text=True)


def test_intercept_logs_activity(client):
    before = len(ACTIVITY_LOG)
    client.get("/intercept", query_string={"target": "https://example.com/logged"})
    assert len(ACTIVITY_LOG) == before + 1
    assert ACTIVITY_LOG[0]["input"] == "https://example.com/logged"


def test_existing_routes_still_work(client):
    for route in ["/", "/url", "/mail", "/history"]:
        assert client.get(route).status_code == 200
    response = client.post("/predict-url", json={"url": "https://example.com"})
    assert response.status_code == 200
    assert "risk_score" in response.get_json()
