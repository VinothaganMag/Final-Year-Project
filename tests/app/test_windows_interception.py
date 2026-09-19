import os
import sys
from unittest.mock import patch

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import cris_launcher
import register_windows_handler
from app import ACTIVITY_LOG, app  # type: ignore[attr-defined]


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_build_intercept_url_valid():
    url = "https://phishing-site.example.com/login?id=123"
    intercept_url = cris_launcher.build_intercept_url(url, caller_hwnd=12345)
    assert intercept_url.startswith("http://127.0.0.1:5000/intercept?target=")
    assert "source=desktop" in intercept_url
    assert "caller_hwnd=12345" in intercept_url
    assert "phishing-site.example.com" in intercept_url


@pytest.mark.parametrize(
    "invalid_url",
    ["", "   ", "ftp://example.com", "javascript:alert(1)", "https://"],
)
def test_build_intercept_url_invalid(invalid_url):
    with pytest.raises(ValueError):
        cris_launcher.build_intercept_url(invalid_url)


def test_find_real_browser_returns_cmd():
    cmd = cris_launcher.find_real_browser()
    assert isinstance(cmd, list)
    assert len(cmd) > 0


@patch("subprocess.Popen")
def test_launch_url_calls_popen(mock_popen):
    target = "https://example.org/test"
    result_url = cris_launcher.launch_url(target, caller_hwnd=999)
    assert "target=https%3A%2F%2Fexample.org%2Ftest" in result_url
    assert "caller_hwnd=999" in result_url
    assert mock_popen.called
    args, _ = mock_popen.call_args
    launched_cmd = args[0]
    assert launched_cmd[-1] == result_url


def test_flask_intercept_supports_source_desktop_and_hwnd(client):
    before_count = len(ACTIVITY_LOG)
    target = "https://desktop-test.example.com/login"
    response = client.get(
        "/intercept",
        query_string={"target": target, "source": "desktop", "caller_hwnd": "8888"},
    )
    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert target in body
    assert "continueBtn" in body
    assert "leaveBtn" in body
    assert 'data-source="desktop"' in body
    assert 'data-caller-hwnd="8888"' in body
    assert len(ACTIVITY_LOG) == before_count + 1


def test_intercept_leave_endpoint(client):
    # Test valid numeric HWND payload
    res = client.post("/intercept/leave", json={"caller_hwnd": 12345})
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["status"] == "ok"
    assert "focused" in json_data

    # Test invalid / missing HWND handles safely
    res_bad = client.post("/intercept/leave", json={"caller_hwnd": "invalid"})
    assert res_bad.status_code == 200
    assert res_bad.get_json()["status"] == "ok"


def test_register_windows_handler_paths_and_status():
    py_exe, script_path, cfg_path = register_windows_handler.get_paths()
    assert os.path.exists(script_path)
    status = register_windows_handler.check_registration_status()
    assert "registered" in status
    assert "platform" in status


def test_detect_and_save_real_browser(tmp_path):
    cfg_file = str(tmp_path / "cris_config.json")
    browser = register_windows_handler.detect_and_save_real_browser(cfg_file)
    assert os.path.exists(cfg_file)
