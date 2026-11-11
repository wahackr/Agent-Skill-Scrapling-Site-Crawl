---
name: scrapling-site-crawl
description: Crawl a website with Scrapling and export discovered same-domain URLs, HTTP statuses, redirects, and request errors to CSV. Use for website URL inventories and link status audits.
---

# Scrapling site crawl

Run the bundled script with the user's starting URL and chosen output path:

```bash
uv run /path/to/scrapling-site-crawl/scripts/crawl_site.py https://example.com/ --output /path/to/urls.csv
```

Resolve the script relative to this skill directory. Its inline dependency metadata lets `uv` install Scrapling's `fetchers` extra without depending on a particular project. No browser installation is required.

Default scope includes the starting hostname and its `www`/non-`www` counterpart. `--include-subdomains` also permits descendants of that hostname after removing `www.`; starting at `shop.example.com` does not include sibling subdomains. External links are excluded, and external redirects are recorded without being followed.

Optional flags:

- `--max-pages 100`: cap attempted requests. Default `0` drains the discovered queue without a fixed limit.
- `--delay 0.5`: seconds between requests, default 0.5.
- `--timeout 30`: timeout per request in seconds.

The CSV columns are `url`, `http_status`, `redirect_to`, `discovered_from`, and `error`. It includes linked files such as PDFs. Redirect source URLs retain their actual 3xx status, with same-domain targets queued separately. DNS, TLS, and timeout failures have a blank status and an error message, never a fabricated HTTP code. Discovered URLs left unvisited by a limit or Ctrl+C have a blank status and `not_fetched`. Output is UTF-8 with a BOM for Excel; an existing output file is overwritten.

The script exits 0 when discovery drains with no request exceptions, 1 for a limit or request exceptions, and 130 for Ctrl+C. HTTP 4xx/5xx responses are valid inventory results and do not alone cause a nonzero exit. Review the summary and CSV before reporting completion. Link the output and mention request failures or unvisited URLs.

Describe the result as **discovered URLs**, not every URL that exists on the website. Discovery follows HTML anchor/area links and HTTP redirects. It does not render JavaScript, submit forms, consult sitemaps or robots.txt, or find unlinked pages. URL fragments are deduplicated, while query strings are preserved. Query-driven navigation can generate an unbounded number of URLs; use the optional limit when appropriate and report that the result is partial.
