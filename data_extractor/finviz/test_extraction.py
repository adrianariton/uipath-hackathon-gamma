"""
CLI entrypoint that:
- extracts tickers/context from a prompt (OpenRouter Gemini via EntityExtractor)
- fetches Finviz news/metrics for those tickers
- saves the combined data to JSON for visualization.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from typing import Dict

from dotenv import load_dotenv

from entity_extractor import EntityExtractor
from financial_data import FinvizScraper, TickerData


def _default_output_path(prompt: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", prompt).strip("_").lower()
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    name = slug or "result"
    return f"{name}_{timestamp}.json"


def extract_and_fetch(prompt: str, top_k_news: int = 10, history_limit: int = 180) -> Dict:
    """
    Extract tickers/context from prompt, then fetch Finviz data.
    Returns a plain dict ready to serialize.
    """
    extractor = EntityExtractor()
    extraction = extractor.extract(prompt)
    tickers = extraction.tickers

    scraper = FinvizScraper()
    finviz_data: Dict[str, TickerData] = scraper.get_data(tickers, top_k=top_k_news, history_limit=history_limit)

    return {
        "prompt": prompt,
        "tickers": extraction.tickers,
        "companies": extraction.companies,
        "context": extraction.context,
        "financial_data": {t: data.model_dump() for t, data in finviz_data.items()},
    }


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Extract financial entities and fetch Finviz data.")
    parser.add_argument("prompt", type=str, help="Prompt describing the companies/context to analyze.")
    parser.add_argument("--top-k-news", type=int, default=10, help="Number of news items per ticker to keep.")
    parser.add_argument(
        "--history-limit",
        type=int,
        default=180,
        help="Number of most recent historical price rows to keep (daily from Stooq).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Path to save JSON results (default: derived from prompt).",
    )
    args = parser.parse_args()

    output_path = args.output or _default_output_path(args.prompt)
    result = extract_and_fetch(args.prompt, top_k_news=args.top_k_news, history_limit=args.history_limit)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Saved results to {output_path}")


if __name__ == "__main__":
    main()
