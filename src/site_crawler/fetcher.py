"""HTTP fetching with per-thread connection pooling."""

from __future__ import annotations

from threading import local
from urllib.parse import urljoin, urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_thread_local = local()


def _session() -> requests.Session:
    """Create one session per worker thread; requests.Session is not shared across threads."""
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        retry = Retry(
            total=2,
            connect=2,
            read=1,
            status=2,
            backoff_factor=0.25,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET", "HEAD"}),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({"User-Agent": "ZegoSiteCrawler/1.0 (+educational crawler)"})
        _thread_local.session = session
    return session


def fetch_html(url: str, timeout: float = 10.0) -> str | None:
    """Fetch HTML, following only redirects that remain on the original hostname."""
    original_host = urlsplit(url).hostname
    current_url = url
    session = _session()

    try:
        # Follow redirects manually so requests never automatically fetches an external host.
        for _ in range(6):
            response = session.get(
                current_url,
                timeout=(min(timeout, 5.0), timeout),
                allow_redirects=False,
            )
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                if not location:
                    return None
                redirected_url = urljoin(current_url, location)
                if urlsplit(redirected_url).hostname is None or urlsplit(redirected_url).hostname.lower() != (original_host or "").lower():
                    return None
                current_url = redirected_url
                continue

            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and "html" not in content_type:
                return None
            # Requests decodes response text according to HTTP headers / HTML heuristics.
            return response.text
        return None  # Redirect loop / excessive redirect chain.
    except requests.RequestException:
        return None
