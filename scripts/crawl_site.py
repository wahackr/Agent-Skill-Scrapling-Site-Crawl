#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["scrapling[fetchers]>=0.5.1,<0.6"]
# ///
"""Discover same-domain links with Scrapling and export URLs and statuses to CSV."""

import argparse
import csv
import math
import sys
import time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from curl_cffi.requests.exceptions import RequestException
from scrapling.fetchers import FetcherSession
from scrapling.spiders import LinkExtractor


FIELDS = ("url", "http_status", "redirect_to", "discovered_from", "error")


def normalize_url(value):
    """Remove fragments and normalize hosts without changing query parameters."""
    try:
        parts = urlsplit(value.strip())
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            return None
        if parts.username is not None or parts.password is not None:
            return None
        host = parts.hostname.encode("idna").decode("ascii").lower()
        host = f"[{host}]" if ":" in host else host
        port = parts.port
        if port is not None and (parts.scheme.lower(), port) not in {("http", 80), ("https", 443)}:
            host = f"{host}:{port}"
        return urlunsplit((parts.scheme.lower(), host, parts.path or "/", parts.query, ""))
    except (ValueError, UnicodeError):
        return None


def crawl(start_url, output, *, include_subdomains=False, max_pages=0, delay=0.5, timeout=30):
    """Fetch each discovered URL once; return counts and whether the queue drained."""
    start_url = normalize_url(start_url)
    if not start_url:
        raise ValueError("Provide an absolute HTTP or HTTPS URL.")
    hostname = urlsplit(start_url).hostname
    # Treat www.example.com and example.com as the same website by default.
    domain = hostname.removeprefix("www.")

    def in_scope(url):
        host = urlsplit(url).hostname
        return host in {domain, f"www.{domain}"} or (
            include_subdomains and host.endswith("." + domain)
        )

    pending = deque()
    records = {}

    def discover(candidate, source=""):
        url = normalize_url(candidate)
        if url and in_scope(url) and url not in records:
            records[url] = dict(zip(FIELDS, (url, "", "", source, "not_fetched")))
            pending.append(url)

    discover(start_url)
    # Include linked files too, so PDFs and other downloads receive status rows.
    # Preserve query order: sorting it can change how some websites interpret URLs.
    extractor = LinkExtractor(deny_extensions=(), canonicalize=False)
    attempted = 0
    interrupted = False
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Write rows as they complete so a partial report survives interruption.
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        stream.flush()
        try:
            # Follow redirects manually to record their original status and avoid
            # fetching an external website through an automatic redirect.
            with FetcherSession(follow_redirects=False, timeout=timeout, retries=1) as session:
                while pending and (not max_pages or attempted < max_pages):
                    if attempted:
                        time.sleep(delay)
                    url = pending.popleft()
                    row = records[url]
                    attempted += 1
                    try:
                        response = session.get(url)
                    except RequestException as exc:
                        row["error"] = f"{type(exc).__name__}: {exc}"
                    else:
                        row["http_status"] = response.status
                        row["error"] = ""
                        # Normalize header names since Scrapling exposes a dict.
                        headers = {key.lower(): value for key, value in response.headers.items()}
                        location = headers.get("location")
                        if response.status in {301, 302, 303, 307, 308} and location:
                            target = urljoin(url, location)
                            row["redirect_to"] = target
                            discover(target, url)
                        # Parse HTML only, while still reporting statuses for files.
                        content_type = headers.get("content-type", "").lower()
                        if "text/html" in content_type or "application/xhtml+xml" in content_type:
                            for link in extractor.extract(response):
                                discover(link, url)
                    writer.writerow(row)
                    stream.flush()
                    print(f"[{attempted}] {row['http_status'] or 'ERROR'} {url}", file=sys.stderr)
        except KeyboardInterrupt:
            interrupted = True
            print("Interrupted; saving discovered URLs to the partial report.", file=sys.stderr)
        finally:
            # Include discovered but unvisited links when limited or interrupted.
            for row in records.values():
                if row["error"] == "not_fetched":
                    writer.writerow(row)

    complete = not interrupted and not pending and not any(
        row["error"] == "not_fetched" for row in records.values()
    )
    failures = sum(bool(row["error"]) and row["error"] != "not_fetched" for row in records.values())
    print(
        f"Saved {len(records)} URLs to {output}; attempted {attempted}, "
        f"request errors {failures}. Discovery {'finished' if complete else 'incomplete'}.",
        file=sys.stderr,
    )
    return {"discovered": len(records), "attempted": attempted, "failures": failures,
            "complete": complete, "interrupted": interrupted}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Starting URL, including https:// or http://")
    parser.add_argument("-o", "--output", type=Path, default=Path("urls.csv"))
    parser.add_argument("--include-subdomains", action="store_true",
                        help="Also crawl subdomains of the starting host (after removing www.)")
    parser.add_argument("--max-pages", type=int, default=0, help="Maximum requests; 0 means unlimited")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between requests (default: 0.5)")
    parser.add_argument("--timeout", type=float, default=30, help="Timeout per request in seconds")
    args = parser.parse_args()
    if args.max_pages < 0 or not math.isfinite(args.delay) or args.delay < 0:
        parser.error("--max-pages and --delay must be nonnegative")
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be positive")
    if not normalize_url(args.url):
        parser.error("url must be an absolute HTTP or HTTPS URL without credentials")
    result = crawl(args.url, args.output, include_subdomains=args.include_subdomains,
                   max_pages=args.max_pages, delay=args.delay, timeout=args.timeout)
    return 130 if result["interrupted"] else (0 if result["complete"] and not result["failures"] else 1)


if __name__ == "__main__":
    raise SystemExit(main())
