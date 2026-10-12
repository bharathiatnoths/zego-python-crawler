"""URL validation, normalisation and same-host rules."""

from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit

SUPPORTED_SCHEMES = {"http", "https"}


def normalise_url(url: str, *, base_url: str | None = None) -> str | None:
    """Return a fetchable absolute HTTP(S) URL, or None for unsupported/invalid URLs.

    Fragments are removed because they identify a location within a document, not a
    separately fetchable resource. Query strings are retained because they can change
    the server response. We intentionally do not rewrite trailing slashes or query
    parameters, as those can be meaningful to a site.
    """
    if not isinstance(url, str) or not url.strip():
        return None

    candidate = url.strip()
    if base_url:
        candidate = urljoin(base_url, candidate)
    candidate, _fragment = urldefrag(candidate)

    try:
        parts = urlsplit(candidate)
        scheme = parts.scheme.lower()
        hostname = parts.hostname
        # Accessing .port also validates malformed port numbers.
        port = parts.port
    except ValueError:
        return None

    if scheme not in SUPPORTED_SCHEMES or not hostname:
        return None

    # Normalise scheme and host casing, and remove default ports.
    host = hostname.lower()
    netloc = host
    if ":" in host and not host.startswith("["):
        netloc = f"[{host}]"
    if port is not None and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{netloc}:{port}"

    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def is_same_host(url: str, base_host: str) -> bool:
    """Use exact hostname equality; example.com.evil and sub.example.com are excluded."""
    try:
        return urlsplit(url).hostname is not None and urlsplit(url).hostname.lower() == base_host.lower()
    except ValueError:
        return False


def extract_links(html: str, page_url: str, base_host: str | None = None) -> list[str]:
    """Extract unique, normalised HTTP(S) anchor links, including external destinations.

    `base_host` is accepted for backwards compatibility with callers but filtering is
    deliberately done by the crawler: external links should be reported in page output,
    but must never be scheduled for fetching.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    found: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        normalised = normalise_url(anchor.get("href", ""), base_url=page_url)
        if normalised:
            found.add(normalised)
    return sorted(found)
