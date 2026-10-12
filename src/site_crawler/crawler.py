"""Concurrent breadth-first crawler."""

from __future__ import annotations

from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from site_crawler.fetcher import fetch_html
from site_crawler.urls import extract_links, is_same_host, normalise_url


@dataclass(slots=True)
class CrawlResult:
    """Information collected for a single successfully fetched HTML page."""

    url: str
    links: list[str] = field(default_factory=list)


class Crawler:
    """Crawl links on the exact hostname of the supplied start URL.

    URLs are marked as discovered before they are submitted to workers. This avoids
    duplicate in-flight requests when multiple pages link to the same destination.
    The frontier is processed in concurrent waves, preserving breadth-first discovery
    while allowing network requests in each wave to run in parallel.
    """

    def __init__(
        self,
        start_url: str,
        *,
        workers: int = 8,
        timeout: float = 10.0,
        max_pages: int = 10_000,
    ) -> None:
        normalised = normalise_url(start_url)
        if not normalised:
            raise ValueError("start URL must be a valid absolute HTTP or HTTPS URL")
        if workers < 1:
            raise ValueError("workers must be at least 1")
        if timeout <= 0:
            raise ValueError("timeout must be greater than 0")
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")

        self.start_url = normalised
        self.base_host = urlsplit(normalised).hostname or ""
        self.workers = workers
        self.timeout = timeout
        self.max_pages = max_pages

    def _crawl_one(self, url: str) -> CrawlResult:
        html = fetch_html(url, timeout=self.timeout)
        if html is None:
            return CrawlResult(url=url)
        return CrawlResult(url=url, links=extract_links(html, url, self.base_host))

    def crawl(self) -> list[CrawlResult]:
        """Return results in completion order; failed pages are represented with no links."""
        discovered = {self.start_url}
        frontier: deque[str] = deque([self.start_url])
        results: list[CrawlResult] = []

        with ThreadPoolExecutor(max_workers=self.workers, thread_name_prefix="crawler") as pool:
            while frontier and len(results) < self.max_pages:
                capacity = self.max_pages - len(results)
                wave: list[str] = []
                while frontier and len(wave) < min(self.workers * 4, capacity):
                    wave.append(frontier.popleft())

                futures: dict[Future[CrawlResult], str] = {
                    pool.submit(self._crawl_one, url): url for url in wave
                }
                for future in as_completed(futures):
                    try:
                        result = future.result()
                    except Exception:
                        # A page-level failure must not stop the entire crawl.
                        result = CrawlResult(url=futures[future])
                    results.append(result)

                    for link in result.links:
                        if is_same_host(link, self.base_host) and link not in discovered:
                            if len(discovered) >= self.max_pages:
                                break
                            discovered.add(link)
                            frontier.append(link)

        return results
