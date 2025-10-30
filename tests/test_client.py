from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pricing_recorder.client import (
    AuthenticationError,
    Century21Client,
    _DEFAULT_USER_AGENT,
)
from pricing_recorder.constants import DEFAULT_BASE_URL


def _mock_response(json_payload: dict | None = None) -> MagicMock:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.status_code = 200
    response.url = DEFAULT_BASE_URL
    if json_payload is not None:
        response.json.return_value = json_payload
    return response


def test_login_bootstraps_session_once(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    session.headers = {}
    bootstrap_response = _mock_response()
    login_response = _mock_response({"SUCCESSMESSAGE": "ok", "ERRORMESSAGE": ""})

    session.get.return_value = bootstrap_response
    session.post.return_value = login_response

    monkeypatch.setattr("pricing_recorder.client.requests.Session", lambda: session)

    client = Century21Client(email="  user@example.com  ", password="  secret  ")

    client.login()
    client.login()  # should not re-bootstrap the session

    session.get.assert_called_once_with(DEFAULT_BASE_URL, timeout=30)
    assert session.post.call_count == 2

    _, kwargs = session.post.call_args
    assert kwargs["data"] == {
        "Action": "SignIn",
        "email": "user@example.com",
        "passwd": "secret",
    }
    headers = kwargs["headers"]
    assert headers["X-Requested-With"] == "XMLHttpRequest"
    assert headers["Origin"] == DEFAULT_BASE_URL.rstrip("/")
    assert headers["User-Agent"] == client.user_agent


def test_login_raises_authentication_error_on_portal_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    session.headers = {}
    bootstrap_response = _mock_response()
    failure_response = _mock_response(
        {"SUCCESSMESSAGE": "", "ERRORMESSAGE": "Authorization failed"}
    )

    session.get.return_value = bootstrap_response
    session.post.return_value = failure_response

    monkeypatch.setattr("pricing_recorder.client.requests.Session", lambda: session)

    client = Century21Client(email="user@example.com", password="secret")

    with pytest.raises(AuthenticationError):
        client.login()


def test_fetch_manufacturer_page_primes_before_request(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    session.headers = {}
    bootstrap_response = _mock_response()
    page_response = _mock_response()
    page_response.text = "<html></html>"

    session.get.side_effect = [bootstrap_response, page_response]

    monkeypatch.setattr("pricing_recorder.client.requests.Session", lambda: session)

    client = Century21Client(email="", password="")

    html = client.fetch_manufacturer_page("Example")

    assert html == "<html></html>"
    assert session.get.call_count == 2
    bootstrap_call, fetch_call = session.get.call_args_list
    assert bootstrap_call.kwargs["timeout"] == 30
    assert bootstrap_call.args[0] == DEFAULT_BASE_URL
    assert fetch_call.args[0].endswith("default.cfm")
    assert fetch_call.kwargs["params"]["pagelink1"] == "Example"


def test_login_requires_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    session.headers = {}

    monkeypatch.setattr("pricing_recorder.client.requests.Session", lambda: session)

    client = Century21Client(email="   ", password="   ")

    with pytest.raises(AuthenticationError):
        client.login()

    session.get.assert_not_called()
    session.post.assert_not_called()


def test_user_agent_defaults_when_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    session.headers = {}
    bootstrap_response = _mock_response()
    login_response = _mock_response({"SUCCESSMESSAGE": "ok", "ERRORMESSAGE": ""})

    session.get.return_value = bootstrap_response
    session.post.return_value = login_response

    monkeypatch.setattr("pricing_recorder.client.requests.Session", lambda: session)

    client = Century21Client(email="user@example.com", password="secret", user_agent="   ")
    client.login()

    assert client.user_agent == _DEFAULT_USER_AGENT
    headers = session.post.call_args.kwargs["headers"]
    assert headers["User-Agent"] == _DEFAULT_USER_AGENT


def test_prime_session_canonicalizes_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    session.headers = {}
    bootstrap_response = _mock_response()
    bootstrap_response.url = "https://redirected.example.com/index.cfm"
    manufacturer_response = _mock_response()
    manufacturer_response.text = "<html></html>"

    session.get.side_effect = [bootstrap_response, manufacturer_response]

    monkeypatch.setattr("pricing_recorder.client.requests.Session", lambda: session)

    client = Century21Client(email="", password="", base_url="https://21stcenturydist.com")

    html = client.fetch_manufacturer_page("Example")

    assert html == "<html></html>"
    assert client.base_url == "https://redirected.example.com/"
    assert session.headers["Referer"] == "https://redirected.example.com/"

    # The second GET call should target the canonicalized host.
    _, fetch_kwargs = session.get.call_args_list[1]
    fetch_url = session.get.call_args_list[1].args[0]
    assert fetch_url.startswith("https://redirected.example.com/")
    assert fetch_kwargs["timeout"] == 30
