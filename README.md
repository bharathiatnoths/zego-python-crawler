# Zego Python Developer Test — Site Crawler

A command-line website crawler that starts from a supplied HTTP(S) URL, prints each fetched page and the same-host links found on that page, and does not crawl external domains or subdomains.

## Features

- Concurrent HTTP fetching using `ThreadPoolExecutor`.
- Exact-host filtering: `example.com` is in scope; `shop.example.com` and `example.com.other.test` are not.
- URL normalisation, relative-link resolution, fragment removal and duplicate suppression.
- Per-thread `requests.Session` instances for connection reuse without sharing a mutable session between worker threads.
- Bounded request timeouts and retries for selected transient HTTP errors, including support for `Retry-After`.
- Configurable worker count and a maximum-page safety limit.
- Unit tests for URL handling, domain filtering, duplicate suppression, failure handling and page limits.

## Requirements

- Python 3.10+
- Internet access for crawling a live website

## Install and run

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
site-crawler https://example.com
```

You can also run it without installing the command-line entry point:

```bash
PYTHONPATH=src python -m site_crawler.cli https://example.com
```

Optional settings:

```bash
site-crawler https://example.com --workers 12 --timeout 8 --max-pages 5000
```

The output contains each page URL and the unique, normalised same-host anchor links extracted from its HTML. Failed or non-HTML pages are still reported, with no discovered links.

## Run the tests

```bash
python -m pip install -e '.[test]'
pytest
```

The tests do not need external network access. HTTP fetching is replaced with controlled test responses for deterministic behaviour.

## Design decisions and trade-offs

### 1. Concurrency model

Crawling is I/O-bound: a large part of the elapsed time is spent waiting for servers to respond. A thread pool can overlap those waits without the complexity of an asynchronous event loop. The worker count is configurable, and requests are submitted in bounded waves rather than creating an unbounded number of futures at once.

**Trade-off:** threads are straightforward and fit a small command-line crawler, but very large crawls may benefit from an async HTTP client and a durable work queue. Increasing concurrency can overload a target site, so production deployments should add per-host rate limiting and honour site policies.

### 2. Domain scope

The crawler compares the parsed hostname using exact equality. This deliberately excludes subdomains as required. It accepts only HTTP and HTTPS URLs and ignores links such as `mailto:`, `javascript:` and other non-web schemes.

**Trade-off:** exact hostname equality is stricter than treating all subdomains as part of one registrable domain, but it matches the stated requirement and avoids accidentally crawling a separate service. A future multi-domain mode should use an explicit allowlist rather than weakening this check.

### 3. URL normalisation and deduplication

Relative URLs are resolved against the page URL. Fragments are removed because they normally point to a section of the same document rather than a separate server resource. Query strings are retained because they may affect the response. URLs are marked as discovered before being scheduled, which prevents multiple pages from queuing the same target at the same time.

**Trade-off:** query strings can create many URL variants or crawl traps. Removing or sorting query parameters globally can break sites where parameter order or values are meaningful. A production crawler could provide configurable canonicalisation rules, query-parameter allowlists, URL budgets, and per-path limits.

### 4. HTTP and connection management

Each worker thread owns a `requests.Session`, allowing keep-alive connection reuse without sharing a mutable session across threads. Connect/read timeouts prevent a slow server from blocking a worker indefinitely. A limited retry policy covers selected transient failures and respects `Retry-After` when supplied.

**Trade-off:** retries improve resilience but increase total traffic and latency. Some HTTP errors are permanent and should not be retried. A production implementation would make retry policy configurable and report the final status code and reason for each failure.

### 5. Parsing and scope of extracted links

Beautiful Soup parses HTML using Python's built-in HTML parser. The implementation extracts anchor `href` values, resolves them to absolute URLs, filters them to the exact host, deduplicates them and sorts them for stable output.

**Trade-off:** this intentionally treats navigational hyperlinks as crawl links. It does not crawl image, script, stylesheet, iframe or form-action URLs. If “all URLs” were intended to include every URL-bearing HTML attribute, extraction could be extended to a documented list of tags and attributes. JavaScript-generated links are not available from static HTML; browser automation is explicitly out of scope.

### 6. Failure handling and output

A failed fetch does not stop the entire crawl. The page is still included in output, but no links are reported for it. The CLI writes human-readable results to standard output and uses command-line argument validation for invalid configuration.

**Trade-off:** returning an empty link list alone does not distinguish a genuine page with no links from a failed request. For production use, the result model and output should include status code, content type, elapsed time, retry count and error reason, with JSON Lines output available for downstream processing.

### 7. Resource limits

A configurable maximum page count provides a safety boundary for sites with infinite calendars, faceted search URLs or other crawl traps. The frontier and futures are bounded in batches, rather than scheduling every discovered URL at once.

**Trade-off:** reaching the page limit means the crawl is incomplete. A production crawler should clearly report that it stopped due to the limit and could persist its frontier for later continuation.

## Complexity

Let `V` be the number of pages fetched and `E` the number of anchor links examined. URL discovery and set membership are expected O(1) on average, so traversal work is approximately O(V + E), excluding network latency and HTML parsing. Memory usage is O(V + E) in this implementation because discovered URLs and results are retained for final output. For very large sites, results and crawl state should be streamed to durable storage instead of held entirely in memory.

## Possible production extensions

- Respect `robots.txt`, add a configurable per-host crawl delay, and identify the crawler clearly.
- Add structured JSON logging, metrics, tracing and a summary of fetched/failed/skipped URLs.
- Persist crawl state and use a durable queue for resumable, distributed crawling.
- Add per-host rate limiting, circuit breaking and adaptive concurrency based on server responses.
- Improve canonicalisation and add URL-pattern/query-parameter rules to avoid crawl traps.
- Add content-type and maximum-response-size controls to protect memory.
- Support multiple explicitly configured hosts and independent per-host limits.
- Expose crawling as a scheduled service or API for large/repeated jobs instead of a one-off CLI.
- Add integration tests against a local HTTP test server, plus load tests and benchmarks on a controlled site.

## Development workflow and AI-tool disclosure

Fill in this section accurately before submission. The exercise specifically asks you to describe the tools you used, so do not claim tools or validation steps that you did not perform.

Suggested details to record:

- **IDE/editor:** [e.g. VS Code / PyCharm and version]
- **Python environment:** [Python version, virtual environment]
- **Documentation consulted:** Python `concurrent.futures`, `urllib.parse`, Requests, Beautiful Soup and pytest documentation.
- **AI assistance:** [Name the tools actually used and explain whether they helped brainstorm architecture, review code, generate tests, or explain trade-offs. State that you reviewed and ran the code yourself, only if true.]
- **Validation performed:** [Record the exact commands run, test results, lint/type-check results, and any manual tests.]

AI tools can speed up exploration, but generated code should be reviewed for correctness, security, licensing and fit with the requirements. Keep the final account of your workflow transparent and specific.

## Assumptions and limitations

- “Single domain and not subdomains” means exact hostname equality with the starting URL.
- Only anchor links (`<a href="...">`) are considered crawl links.
- Fragments are removed; query strings are retained.
- The crawler fetches static HTML only and does not execute JavaScript.
- The maximum page count is a safety limit; reaching it may leave links unvisited.
- This is a focused hiring exercise, not a full web-scale crawler. Before production use, add robots-policy handling, explicit rate limiting, richer status reporting and durable crawl state.
