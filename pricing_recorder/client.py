"""HTTP client for interacting with 21st Century Distributing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests

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
    base_url: str = "https://21stcenturydist.com/"
    user_agent: str = _DEFAULT_USER_AGENT
    timeout: int = 30
    _session: requests.Session = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": self.base_url,
            }
        )
        if not self.base_url.endswith("/"):
            self.base_url = f"{self.base_url}/"

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def login(self) -> None:
        """Authenticate the session using the stored credentials."""

        payload = {"Action": "SignIn", "email": self.email, "passwd": self.password}
        response = self._session.post(
            self._url("generalActions.cfm"), data=payload, timeout=self.timeout
        )
        self._ensure_success(response)

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

        params = {"pagelink": "manufacturer", "pagelink1": manufacturer, "logo": "Y"}
        response = self._session.get(
            self._url("default.cfm"), params=params, timeout=self.timeout
        )
        self._ensure_success(response)
        return response.text

    def fetch_item_page(self, item_code: str) -> str:
        """Return the raw HTML for a specific item detail page."""

        params = {"itemsearch": item_code, "page": "products", "searchcode": "N"}
        response = self._session.get(
            self._url("default.cfm"), params=params, timeout=self.timeout
        )
        self._ensure_success(response)
        return response.text

    def download_price_sheet(self, manufacturer: str) -> bytes:
        """Download the manufacturer PDF price sheet."""

        params = {"manufacturer": manufacturer}
        response = self._session.get(
            self._url("priceSheetPDF.cfm"), params=params, timeout=self.timeout
        )
        self._ensure_success(response)
        return response.content

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _url(self, path: str) -> str:
        return urljoin(self.base_url, path)

    def _ensure_success(self, response: requests.Response) -> None:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:  # pragma: no cover - network failure
            raise RequestFailed(str(exc)) from exc

    @property
    def session(self) -> requests.Session:
        """Expose the underlying session for advanced use cases."""

        return self._session
