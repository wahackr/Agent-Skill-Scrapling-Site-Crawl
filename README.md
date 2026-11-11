# Scrapling Site Crawl

A reusable agent skill and standalone Python script that crawls a website with
[Scrapling](https://github.com/D4Vinci/Scrapling) and exports discovered same-domain
URLs, HTTP statuses, redirects, and request errors to CSV.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Python 3.10 or newer, which uv can provision

The script declares its dependencies inline. Running it with uv installs
`scrapling[fetchers]` automatically. No browser installation is required.

## Usage

From this repository's root:

```bash
uv run scripts/crawl_site.py https://www.alohaonline.asia/ --output aloha-urls.csv
```

Limit a crawl to 100 attempted requests:

```bash
uv run scripts/crawl_site.py https://example.com/ --output urls.csv --max-pages 100
```

Include subdomains and adjust request timing:

```bash
uv run scripts/crawl_site.py https://example.com/ \
  --include-subdomains --delay 1 --timeout 20 --output urls.csv
```

| Option | Default | Description |
| --- | --- | --- |
| `url` | Required | Absolute starting URL, including `https://` or `http://` |
| `-o`, `--output` | `urls.csv` | Destination CSV; overwrites an existing file |
| `--include-subdomains` | Off | Include descendants of the starting hostname after removing `www.` |
| `--max-pages` | `0` | Maximum attempted requests; `0` means unlimited |
| `--delay` | `0.5` | Seconds between requests |
| `--timeout` | `30` | Timeout per request in seconds |

## CSV output

| Column | Meaning |
| --- | --- |
| `url` | Discovered URL, with its fragment removed |
| `http_status` | HTTP response code, such as `200`, `301`, or `404`; blank if no response was received or no request was attempted |
| `redirect_to` | Absolute redirect target, when supplied by a redirect response |
| `discovered_from` | First page that linked or redirected to this URL; blank for the starting URL |
| `error` | Request error, `not_fetched` for an unvisited URL, or blank for a received response |

The CSV uses UTF-8 with a BOM for Excel compatibility. HTTP errors such as 404 and
500 retain their actual status. Connection, DNS, TLS, and timeout failures have a
blank status and an explanatory error.

Redirects retain the source URL's 3xx status. In-scope targets are queued
separately; external targets are recorded without being fetched. Linked files,
including PDFs, are checked too.

Press Ctrl+C to stop and save a partial report. Discovered URLs that remain
unvisited are included with `error=not_fetched`. The same applies when the request
limit is reached.

Exit codes: `0` when the queue drains without request exceptions, `1` for a
request limit or request exceptions, and `130` for Ctrl+C. HTTP 4xx/5xx responses
alone do not cause a nonzero exit.

## Crawl scope and limits

- By default, the starting hostname and its `www`/non-`www` counterpart are in scope.
- With `--include-subdomains`, starting at `example.com` includes `shop.example.com`.
  Starting at `shop.example.com` does not include sibling subdomains.
- Duplicate URLs are fetched once. Fragments are removed; query strings and their
  parameter order are preserved.
- Discovery follows HTML anchor/area links and HTTP redirects. It does not render
  JavaScript, submit forms, read sitemaps or robots.txt, or discover unlinked pages.
- Query-driven navigation can produce an unlimited number of URLs. Use
  `--max-pages` when a bounded crawl is needed.

The result is an inventory of **discovered URLs**, rather than a guarantee of every
URL that exists on the website.

## Agent skill

[SKILL.md](SKILL.md) contains the agent instructions. Keep it together with
`scripts/crawl_site.py` when copying this folder into your agent's skills directory.

Example request:

> Use scrapling-site-crawl to crawl https://example.com/ and save discovered URLs
> and HTTP statuses to example-urls.csv.
