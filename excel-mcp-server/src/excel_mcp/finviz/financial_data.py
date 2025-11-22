"""
Finviz scraper to pull news and snapshot metrics for one or more tickers.
Also augments with lightweight historical daily prices (via Stooq).
"""

from __future__ import annotations

import re
from urllib.parse import urljoin
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    headline: str
    source: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[str] = None


class HistoricalBar(BaseModel):
    date: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None


class TickerData(BaseModel):
    news: List[NewsItem] = Field(default_factory=list)
    metrics: Dict[str, str] = Field(default_factory=dict)
    historical: List[HistoricalBar] = Field(default_factory=list)
    
    


class FinvizScraper:
    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.base_url = "https://finviz.com/quote.ashx"
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def get_data(self, tickers: List[str], top_k: int = 10, history_limit: int = 180) -> Dict[str, TickerData]:
        """
        Fetch news (top_k) and snapshot metrics for the provided tickers.
        """
        results: Dict[str, TickerData] = {}
        for raw_ticker in tickers:
            ticker = raw_ticker.upper().strip()
            if not ticker:
                continue
            try:
                html = self._fetch_ticker_page(ticker)
                soup = BeautifulSoup(html, "html.parser")
                news = self._parse_news(soup, top_k=top_k)
                metrics = self._parse_metrics(soup)
                historical = self._fetch_historical_prices(ticker, limit=history_limit)
                results[ticker] = TickerData(news=news, metrics=metrics, historical=historical)
            except Exception:
                results[ticker] = TickerData()
        return results

    def _fetch_ticker_page(self, ticker: str) -> str:
        response = self.session.get(self.base_url, params={"t": ticker}, timeout=15)
        response.raise_for_status()
        return response.text

    def _parse_news(self, soup: BeautifulSoup, top_k: int) -> List[NewsItem]:
        table = soup.find("table", class_=re.compile(r"news-table|fullview-news-outer"))
        if not table:
            return []

        items: List[NewsItem] = []
        last_date: Optional[str] = None

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            raw_dt = cells[0].get_text(" ", strip=True)
            timestamp = raw_dt or None
            if raw_dt:
                if re.match(r"^[A-Za-z]{3}-\d{2}-\d{2}", raw_dt):
                    last_date = raw_dt.split(" ", 1)[0]
                elif last_date:
                    timestamp = f"{last_date} {raw_dt}"

            link_tag = cells[1].find("a")
            headline = link_tag.get_text(strip=True) if link_tag else cells[1].get_text(" ", strip=True)
            url = link_tag["href"] if link_tag and link_tag.has_attr("href") else None
            url = self._normalize_url(url)
            source_tag = cells[1].find("span", class_=re.compile(r"news-link-left"))
            source = source_tag.get_text(strip=True) if source_tag else None

            items.append(
                NewsItem(
                    headline=headline,
                    source=source,
                    url=url,
                    published_at=timestamp,
                )
            )
            if len(items) >= top_k:
                break

        return items

    def _parse_metrics(self, soup: BeautifulSoup) -> Dict[str, str]:
        metrics: Dict[str, str] = {}
        table = soup.find("table", class_=re.compile(r"snapshot-table2"))
        if not table:
            return metrics

        cells = table.find_all("td")
        for i in range(0, len(cells) - 1, 2):
            key = cells[i].get_text(strip=True)
            val = cells[i + 1].get_text(strip=True)
            if key:
                metrics[key] = val

        return metrics

    def _fetch_historical_prices(self, ticker: str, limit: int) -> List[HistoricalBar]:
        """
        Fetch historical OHLCV data (daily) using Stooq as a lightweight source.
        Returns the most recent `limit` rows (default 180).
        """
        symbols = []
        lower = ticker.lower()
        # Prefer US suffix; also try raw ticker as fallback.
        if not lower.endswith(".us"):
            symbols.append(f"{lower}.us")
        symbols.append(lower)

        for symbol in symbols:
            url = f"https://stooq.pl/q/d/l/?s={symbol}&i=d"
            try:
                resp = self.session.get(url, timeout=15)
                if resp.status_code != 200 or "Data" not in resp.text:
                    continue
                lines = [line.strip() for line in resp.text.splitlines() if line.strip()]
                if len(lines) <= 1:
                    continue
                rows: List[HistoricalBar] = []
                for line in lines[1:]:
                    parts = line.split(",")
                    if len(parts) != 6:
                        continue
                    date, o, h, l, c, v = parts
                    try:
                        bar = HistoricalBar(
                            date=date,
                            open=float(o) if o else None,
                            high=float(h) if h else None,
                            low=float(l) if l else None,
                            close=float(c) if c else None,
                            volume=int(float(v)) if v else None,
                        )
                        rows.append(bar)
                    except ValueError:
                        continue
                if not rows:
                    continue
                if limit and limit > 0:
                    rows = rows[-limit:]
                return rows
            except Exception:
                continue

        return []

    def _normalize_url(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        cleaned = url.strip()
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            return cleaned
        return urljoin("https://finviz.com/", cleaned)
