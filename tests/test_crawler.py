from site_crawler.crawler import Crawler


class FakeResponse:
    def __init__(self, text):
        self.text = text


def test_crawler_visits_each_same_host_url_once(monkeypatch):
    pages = {
        "https://example.com/": '<a href="/a">A</a><a href="/b">B</a><a href="https://outside.test/">Out</a>',
        "https://example.com/a": '<a href="/">Home</a><a href="/b#top">B</a>',
        "https://example.com/b": '<a href="/a">A</a>',
    }
    seen = []

    def fake_fetch(url, timeout=10.0):
        seen.append(url)
        return pages[url]

    monkeypatch.setattr("site_crawler.crawler.fetch_html", fake_fetch)
    results = Crawler("https://example.com", workers=3).crawl()

    assert {result.url for result in results} == set(pages)
    assert len(seen) == len(set(seen)) == 3
    root = next(result for result in results if result.url == "https://example.com/")
    assert root.links == ["https://example.com/a", "https://example.com/b", "https://outside.test/"]
    assert "https://outside.test/" not in {result.url for result in results}


def test_failed_page_does_not_stop_crawl(monkeypatch):
    def fake_fetch(url, timeout=10.0):
        if url == "https://example.com/":
            return '<a href="/next">Next</a>'
        return None

    monkeypatch.setattr("site_crawler.crawler.fetch_html", fake_fetch)
    results = Crawler("https://example.com", workers=2).crawl()
    assert {result.url for result in results} == {"https://example.com/", "https://example.com/next"}
    failed = next(result for result in results if result.url.endswith("/next"))
    assert failed.links == []


def test_max_pages_is_respected(monkeypatch):
    monkeypatch.setattr(
        "site_crawler.crawler.fetch_html",
        lambda url, timeout=10.0: '<a href="/a">A</a><a href="/b">B</a>',
    )
    results = Crawler("https://example.com", workers=2, max_pages=2).crawl()
    assert len(results) == 2
