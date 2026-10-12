"""Command-line interface."""

from __future__ import annotations

import argparse
import sys

from site_crawler.crawler import Crawler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="site-crawler",
        description="Crawl HTML links on the exact hostname of a starting URL.",
    )
    parser.add_argument("base_url", help="Starting absolute URL, for example https://example.com")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent HTTP workers (default: 8)")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout in seconds (default: 10)")
    parser.add_argument("--max-pages", type=int, default=10_000, help="Safety limit on pages scheduled (default: 10000)")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        crawler = Crawler(
            args.base_url,
            workers=args.workers,
            timeout=args.timeout,
            max_pages=args.max_pages,
        )
        for result in crawler.crawl():
            print(f"Page: {result.url}")
            print("Links:")
            for link in result.links:
                print(f"  {link}")
            print()
    except ValueError as exc:
        parser.error(str(exc))
    except KeyboardInterrupt:
        print("Crawl interrupted.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
