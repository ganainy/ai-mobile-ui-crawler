from unittest.mock import MagicMock, patch

import requests

from mobile_crawler.domain.api_key_check import check_api_key


def _response(status: int) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.ok = 200 <= status < 300
    return response


def test_empty_key_is_not_sent():
    with patch("mobile_crawler.domain.api_key_check.requests.get") as get:
        assert check_api_key("gemini", "  ") == (False, "Enter a key first")
    get.assert_not_called()


def test_gemini_ok():
    with patch("mobile_crawler.domain.api_key_check.requests.get", return_value=_response(200)) as get:
        assert check_api_key("gemini", " abc ") == (True, "Key works")
    assert get.call_args.kwargs["headers"] == {"x-goog-api-key": "abc"}


def test_openrouter_rejected():
    with patch("mobile_crawler.domain.api_key_check.requests.get", return_value=_response(401)):
        assert check_api_key("openrouter", "bad") == (False, "Key rejected")


def test_server_error():
    with patch("mobile_crawler.domain.api_key_check.requests.get", return_value=_response(503)):
        assert check_api_key("openrouter", "k") == (False, "Provider error (HTTP 503)")


def test_network_error():
    with patch("mobile_crawler.domain.api_key_check.requests.get", side_effect=requests.ConnectionError()):
        ok, message = check_api_key("gemini", "k")
    assert not ok
    assert "ConnectionError" in message
