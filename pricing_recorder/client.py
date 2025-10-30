"""HTTP client for interacting with 21st Century Distributing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests

from .constants import DEFAULT_BASE_URL

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)


class AuthenticationError(RuntimeError):
    """Raised when the provided credentials are rejected by the website."""


class RequestFailed(RuntimeError):
    """Raised when a HTTP request fails for any reason."""


@dataclass(slots=True)
class Century21Client:
    """Stateful HTTP client that maintains a logged-in session."""

    email: str
    password: str
    base_url: str = DEFAULT_BASE_URL
    user_agent: str = _DEFAULT_USER_AGENT
    timeout: int = 30
    _session: requests.Session = field(init=False, repr=False)
    _primed: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        self.email = self.email.strip()
        self.password = self.password.strip()
        if not self.user_agent.strip():
            self.user_agent = _DEFAULT_USER_AGENT
        if not self.base_url.endswith("/"):
            self.base_url = f"{self.base_url}/"
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": self.base_url,
            }
        )

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def login(self) -> None:
        """Authenticate the session using the stored credentials."""

        if not self.email or not self.password:
            raise AuthenticationError("Email and password must be provided for login.")
        self._prime_session()

        payload = {"Action": "SignIn", "email": self.email, "passwd": self.password}
        try:
            response = self._session.post(
                self._url("generalActions.cfm"),
                data=payload,
                headers=self._login_headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:  # pragma: no cover - network failure
            raise RequestFailed(f"Login request failed: {exc}") from exc
        self._ensure_success(response, "login request")

        try:
            data: Dict[str, Any] = response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise RequestFailed("Login response did not contain valid JSON") from exc

        if data.get("ERRORMESSAGE"):
            raise AuthenticationError(data["ERRORMESSAGE"])

        if not data.get("SUCCESSMESSAGE"):
            raise AuthenticationError("Login failed without a specific error message.")

    def fetch_manufacturer_page(self, manufacturer: str) -> str:
        """Return the raw HTML for a manufacturer listing page."""

        self._prime_session()
        params = {"pagelink": "manufacturer", "pagelink1": manufacturer, "logo": "Y"}
        try:
            response = self._session.get(
                self._url("default.cfm"), params=params, timeout=self.timeout
            )
        except requests.RequestException as exc:  # pragma: no cover - network failure
            raise RequestFailed(f"Failed to fetch manufacturer page: {exc}") from exc
        self._ensure_success(response, f"fetching manufacturer page for {manufacturer}")
        return response.text

    def fetch_item_page(self, item_code: str) -> str:
        """Return the raw HTML for a specific item detail page."""

        self._prime_session()
        params = {"itemsearch": item_code, "page": "products", "searchcode": "N"}
        try:
            response = self._session.get(
                self._url("default.cfm"), params=params, timeout=self.timeout
            )
        except requests.RequestException as exc:  # pragma: no cover - network failure
            raise RequestFailed(f"Failed to fetch item page: {exc}") from exc
        self._ensure_success(response, f"fetching item page for {item_code}")
        return response.text

    def download_price_sheet(self, manufacturer: str) -> bytes:
        """Download the manufacturer PDF price sheet."""

        self._prime_session()
        params = {"manufacturer": manufacturer}
        try:
            response = self._session.get(
                self._url("priceSheetPDF.cfm"), params=params, timeout=self.timeout
            )
        except requests.RequestException as exc:  # pragma: no cover - network failure
            raise RequestFailed(f"Failed to download price sheet: {exc}") from exc
        self._ensure_success(response, f"downloading price sheet for {manufacturer}")
        return response.content

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _url(self, path: str) -> str:
        return urljoin(self.base_url, path)

    def _prime_session(self) -> None:
        if self._primed:
            return

        try:
            response = self._session.get(self.base_url, timeout=self.timeout)
        except requests.RequestException as exc:  # pragma: no cover - network failure
            raise RequestFailed(f"Session bootstrap failed: {exc}") from exc
        self._ensure_success(response, "session bootstrap")
        self._primed = True

    def _login_headers(self) -> Dict[str, str]:
        origin = self.base_url.rstrip("/")
        return {
            "Referer": self.base_url,
            "Origin": origin,
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": self.user_agent,
        }

    def _ensure_success(self, response: requests.Response, context: str) -> None:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:  # pragma: no cover - network failure
            status = getattr(response, "status_code", None)
            if status == 403:
                raise RequestFailed(
                    "403 Forbidden received during {}. The portal blocked the request; "
                    "verify your network access and supplied User-Agent."
                    .format(context)
                ) from exc
            raise RequestFailed(f"{context} failed: {exc}") from exc
import requests
from urllib.parse import urljoin
from typing import Optional, Dict
import logging
import http.client as http_client

class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

class RequestFailed(Exception):
    """Raised when a request to the site fails."""
    pass

class Century21Client:
    """Client to interact with 21st Century Distributing site."""

    def __init__(self, base_url: str = "https://21stcenturydist.com", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        # Set headers and referer to mimic a browser and set correct referer
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; PricingRecorder/1.0)",
            "Referer": f"{self.base_url}/default.cfm",
        })
        # Initialize cookies by visiting the homepage once
        self._session.get(f"{self.base_url}/default.cfm", timeout=self.timeout)

    def login(self, email: str, password: str) -> None:
        """Login to the site using provided credentials."""
        # Enable verbose HTTP logging
        http_client.HTTPConnection.debuglevel = 1
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

        data = {"email": email, "password": password}
        resp = self._session.post(f"{self.base_url}/default.cfm?login=Y", data=data, timeout=self.timeout)
        # Print session cookies after login
        print("Session cookies after login:", self._session.cookies.get_dict())

        if "Logout" not in resp.text and "Sign Out" not in resp.text:
            raise AuthenticationError("Login failed")

    def fetch_manufacturer_page(self, manufacturer: str) -> str:
        """Return HTML for a manufacturer search page using AJAX endpoint with fallback."""
        # Attempt AJAX search endpoint first
        params_ajax = {"searchterm": manufacturer}
        resp = self._session.get(self._url("ajax/productsearch.cfm"), params=params_ajax, timeout=self.timeout)
        # If no products found, fall back to full search page
        if "productDescription" not in resp.text:
            params_full = {"search": "Y", "searchterm": manufacturer}
            resp = self._session.get(self._url("default.cfm"), params=params_full, timeout=self.timeout)
        self._ensure_success(resp)
        return resp.text

    def fetch_item_page(self, item_code: str) -> str:
        """Return the raw HTML for a specific item detail page."""
        params = {
            "itemsearch": item_code,
            "page": "products",
            "searchcode": "N",
        }
        resp = self._session.get(self._url("default.cfm"), params=params, timeout=self.timeout)
        self._ensure_success(resp)
        return resp.text

    def download_price_sheet(self, manufacturer: str) -> bytes:
        """Download the manufacturer PDF price sheet."""
        params = {"manufacturer": manufacturer}
        resp = self._session.get(self._url("priceSheetPDF.cfm"), params=params, timeout=self.timeout)
        self._ensure_success(resp)
        return resp.content

    # helpers
    def _url(self, path: str) -> str:
        """Build a fully qualified URL for a given path."""
        return urljoin(f"{self.base_url}/", path)

    def _ensure_success(self, response: requests.Response) -> None:
        """Raise RequestFailed if the response contains an HTTP error."""
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RequestFailed(str(exc)) from exc

    @property
    def session(self) -> requests.Session:
        """Expose the underlying session for advanced use cases."""

        return self._session
