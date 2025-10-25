import requests
from urllib.parse import urljoin
from typing import Optional, Dict


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
        data = {"email": email, "password": password}
        resp = self._session.post(f"{self.base_url}/default.cfm?login=Y", data=data, timeout=self.timeout)
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

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
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
