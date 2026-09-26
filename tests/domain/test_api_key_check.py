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


def test_opencode_go_key_checked_with_a_tiny_chat_call():
    with patch("mobile_crawler.domain.api_key_check.requests.post", return_value=_response(200)) as post:
        assert check_api_key("opencode_go", " k ") == (True, "Key works")
    assert post.call_args.args[0].endswith("/chat/completions")
    headers = post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer k"
    assert headers["x-opencode-session"]
    assert headers["User-Agent"].startswith("mobile-crawler/")
    assert post.call_args.kwargs["json"]["max_tokens"] == 16


def test_opencode_go_rejected_key():
    with patch("mobile_crawler.domain.api_key_check.requests.post", return_value=_response(401)):
        assert check_api_key("opencode_go", "bad") == (False, "Key rejected")


def test_opencode_go_limit_reached_still_means_key_works():
    with patch("mobile_crawler.domain.api_key_check.requests.post", return_value=_response(429)):
        ok, message = check_api_key("opencode_go", "k")
    assert ok
    assert "limit" in message


def test_opencode_go_400_means_key_was_accepted():
    with patch("mobile_crawler.domain.api_key_check.requests.post", return_value=_response(400)):
        ok, message = check_api_key("opencode_go", "k")
    assert ok
    assert "400" in message
