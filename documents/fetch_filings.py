#!/usr/bin/env python3
"""
Download the most recent 10-K and 10-Q filings for a handful of large-cap tech
companies. Saves both the raw filing (HTML) and a lightly cleaned text version
for easier ingestion in RAG pipelines.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser
from typing import Dict, Iterable, Optional

# SEC asks for a descriptive User-Agent with contact info.
HTTP_HEADERS = {
    "User-Agent": "uipath-hackathon-gamma/1.0 (contact: contact@example.com)"
}

COMPANIES: Dict[str, Dict[str, str]] = {
    "AAPL": {"name": "Apple Inc.", "cik": "0000320193"},
    "AMZN": {"name": "Amazon.com Inc.", "cik": "0001018724"},
    "MSFT": {"name": "Microsoft Corp.", "cik": "0000789019"},
    "GOOGL": {"name": "Alphabet Inc.", "cik": "0001652044"},
    "NVDA": {"name": "NVIDIA Corp.", "cik": "0001045810"},
}

FORMS: Iterable[str] = ("10-K", "10-Q")
SUBMISSION_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{filename}"


class FilingHTMLTextParser(HTMLParser):
    """Minimal HTML-to-text converter tailored for EDGAR filings."""

    _BLOCK_TAGS = {
        "p",
        "div",
        "br",
        "tr",
        "td",
        "th",
        "li",
        "section",
        "article",
        "table",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    }

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag in {"script", "style"}:
            self._skip_stack.append(tag)
            return
        if tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if self._skip_stack and self._skip_stack[-1] == tag:
            self._skip_stack.pop()
            return
        if tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._skip_stack:
            return
        text = " ".join(data.split())
        if text:
            self._parts.append(text)

    def get_text(self) -> str:
        joined = "".join(self._parts)
        # Normalize whitespace while keeping paragraph breaks readable.
        lines = [line.strip() for line in joined.splitlines()]
        cleaned = "\n".join(line for line in lines if line)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    with urllib.request.urlopen(req) as resp:  # nosec: B310 - SEC endpoint
        return json.load(resp)


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    with urllib.request.urlopen(req) as resp:  # nosec: B310 - SEC endpoint
        return resp.read()


def find_latest_filings(company: Dict[str, str]) -> Dict[str, Dict[str, str]]:
    """Return the most recent 10-K and 10-Q metadata for a company."""
    cik = company["cik"].zfill(10)
    submission = fetch_json(SUBMISSION_URL.format(cik=cik))
    recent = submission["filings"]["recent"]
    forms = recent["form"]
    accessions = recent["accessionNumber"]
    primary_docs = recent["primaryDocument"]
    dates = recent["filingDate"]

    found: Dict[str, Dict[str, str]] = {}
    for idx, form in enumerate(forms):
        if form not in FORMS or form in found:
            continue
        found[form] = {
            "accession": accessions[idx],
            "primary_document": primary_docs[idx],
            "date": dates[idx],
        }
        if len(found) == len(tuple(FORMS)):
            break
    return found


def build_archive_url(cik: str, accession: str, filename: str) -> str:
    return ARCHIVE_URL.format(
        cik=str(int(cik)), accession=accession.replace("-", ""), filename=filename
    )


def html_to_text(content: bytes) -> str:
    text = content.decode("utf-8", errors="replace")
    parser = FilingHTMLTextParser()
    parser.feed(text)
    parser.close()
    extracted = parser.get_text()
    return extracted or text


def save_filing(
    ticker: str, company: Dict[str, str], form: str, filing: Dict[str, str], out_dir: pathlib.Path
) -> None:
    cik = company["cik"]
    archive_url = build_archive_url(
        cik=cik, accession=filing["accession"], filename=filing["primary_document"]
    )
    raw_bytes = fetch_bytes(archive_url)

    date = filing["date"]
    raw_path = out_dir / f"{form}-{date}-raw.html"
    text_path = out_dir / f"{form}-{date}.txt"

    raw_path.write_bytes(raw_bytes)
    text_path.write_text(html_to_text(raw_bytes), encoding="utf-8")
    print(f"[{ticker}] saved {form} dated {date}")


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent
    for ticker, company in COMPANIES.items():
        company_dir = root / ticker
        company_dir.mkdir(parents=True, exist_ok=True)
        try:
            filings = find_latest_filings(company)
        except Exception as exc:  # pragma: no cover - operational fetch
            print(f"[{ticker}] failed to fetch submission index: {exc}", file=sys.stderr)
            continue
        for form in FORMS:
            filing = filings.get(form)
            if not filing:
                print(f"[{ticker}] no recent {form} found", file=sys.stderr)
                continue
            try:
                save_filing(ticker, company, form, filing, company_dir)
            except Exception as exc:  # pragma: no cover - operational fetch
                print(f"[{ticker}] failed to download {form}: {exc}", file=sys.stderr)
            time.sleep(0.5)  # be gentle to the SEC servers
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
