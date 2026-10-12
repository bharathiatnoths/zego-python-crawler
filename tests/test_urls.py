from site_crawler.urls import extract_links, is_same_host, normalise_url


def test_normalise_resolves_relative_urls_and_removes_fragments():
    assert normalise_url("../about#team", base_url="https://Example.com/shop/item") == "https://example.com/about"


def test_normalise_rejects_non_http_schemes_and_invalid_urls():
    assert normalise_url("mailto:hello@example.com") is None
    assert normalise_url("javascript:alert(1)") is None
    assert normalise_url("https://[invalid") is None


def test_same_host_excludes_subdomains_and_lookalikes():
    assert is_same_host("https://example.com/page", "example.com")
    assert not is_same_host("https://shop.example.com/page", "example.com")
    assert not is_same_host("https://example.com.evil.test/page", "example.com")


def test_extract_links_filters_external_links_and_deduplicates():
    html = '''
    <a href="/about">About</a>
    <a href="https://example.com/about#team">About again</a>
    <a href="https://sub.example.com/page">Subdomain</a>
    <a href="https://elsewhere.test/">External</a>
    <a href="mailto:help@example.com">Email</a>
    '''
    assert extract_links(html, "https://example.com/", "example.com") == [
        "https://elsewhere.test/",
        "https://example.com/about",
        "https://sub.example.com/page",
    ]
