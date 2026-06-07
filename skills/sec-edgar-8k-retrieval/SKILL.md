---
name: sec-edgar-8k-retrieval
description: Retrieves a company's most recent 8-K current report and its Exhibit 99.1 earnings press release text from SEC EDGAR via edgartools. Use whenever the task needs an official earnings press release, 8-K event items, or a transcript fallback when earningscall has no coverage for the ticker.
---

# SEC EDGAR 8-K Retrieval

## Purpose
Fetch the latest 8-K and extract the earnings press release (Exhibit 99.1) as clean text,
for any US-listed ticker, free and without an API key.

## Inputs
- `ticker: str`  (e.g. "NVDA")
- `form: str = "8-K"`
- Optional `accession: str` to target a specific filing.

## Outputs
- `press_release_text: str`   # EX-99.1 plain text ("" if none)
- `eight_k_items: list[str]`  # e.g. ["Item 2.02", "Item 9.01"]
- `filing_url: str`, `filing_date: str`

## Tools used
- edgartools: `Company`, `set_identity`, `Filing.obj()` -> `EightK`,
  `EightK.press_releases[0].text()`, `filing.exhibits` / `ex.text()`.

## Agent responsible
Transcript Ingestion agent (fallback path).

## Procedure
1. `set_identity(os.environ["EDGAR_IDENTITY"])`  # "Name email@x.com" — required by SEC.
2. `filing = Company(ticker).get_filings(form="8-K").latest()`  # .latest() returns ONE Filing.
3. `ek = filing.obj()`  # EightK object.
4. If `ek.has_press_release`: `press_release_text = ek.press_releases[0].text()`.
   Else iterate `filing.exhibits`; if `ex.exhibit_number == "99.1"`: `ex.text()`.
5. Record `ek.items`, `filing.filing_date`.

## Edge cases / notes
- `.head(1)` returns a Filings COLLECTION, not a Filing — use `.latest()` or `[0]`.
- Exhibit text getter is `.text()` (a method); there is NO `.content` attribute.
- Some earnings 8-Ks are narrative-only (no parseable tables) → `has_earnings` False
  but `has_press_release` may still be True.
- SEC enforces a 10 req/s courtesy limit; edgartools throttles, but batch politely.
- Pin the version: edgartools releases very frequently; verify with `pip show edgartools`.