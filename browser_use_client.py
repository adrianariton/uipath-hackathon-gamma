import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from mcp.types import Tool, TextContent
import json
async def start_crawl(arguments):
    """Start the data_extractor crawl flow and return the queue index and quick Finviz data.

    This function re-uses the logic from the `data_extractor` package and mirrors
    the behaviour of `data_extractor/main.py`: it extracts tickers from the prompt,
    starts the async crawling agent (which yields a queue index immediately) and
    fetches quick Finviz snapshot data to return to the caller.
    """
    prompt: str = arguments["prompt"] or ""
    company_name  = arguments["company_name"] or ""
    locations = []
    # Import lazily to avoid hard import-time side-effects. Some environments
    # may not have the heavy `browser-use` or Playwright runtime available;
    # fall back to a limited mode that only runs entity extraction + finviz
    # snapshot if the browser agent modules are missing.
    from finviz.entity_extractor import EntityExtractor
    from finviz.financial_data import FinvizScraper
    from browser_use_impl.CrawlInternet import basic_search, QUERIES_RESULTS

    try:
        _has_browser_impl = True
    except Exception:
        basic_search = None
        QUERIES_RESULTS = {}
        _has_browser_impl = False

    # 1) Extract entities (synchronous)
    extractor = EntityExtractor()
    extraction_response = extractor.extract(prompt)
    tickers = extraction_response.tickers
    companies = extraction_response.companies

    if company_name is None and len(companies) > 0:
        company_name = companies[0]

    # 2) Start the async crawling flow and capture the returned queue index.
    # If the browser-based agent isn't available in this environment, skip
    # the agent and return a sentinel `None` for the queue id.
    query_id: Optional[int] = None
    if _has_browser_impl and basic_search is not None:
        async for q in basic_search(company_name, locations):
            query_id = q
            break
    else:
        # Indicate we didn't enqueue a browser agent in this environment.
        query_id = None

    # 3) Fetch Finviz snapshot data in a thread so we don't block the loop
    finviz_scraper = FinvizScraper()
    loop = asyncio.get_running_loop()
    try:
        finviz_data = await loop.run_in_executor(None, finviz_scraper.get_data, tickers, 10, 90)
    except Exception as e:
        logger.exception("Failed to fetch finviz data")
        finviz_data = {}

    # Convert pydantic models to serialisable dicts
    finviz_data_dict = {ticker: data.model_dump() for ticker, data in finviz_data.items()}

    #join the tickers, finviz and company name in a [[str]]
    with open("TICKER_DATA.txt", "w") as f:
        f.write(f"TICKER_DATA: {finviz_data_dict}")
    return [TextContent(text=f"Te rog parseaza JSON-ul, te rog eu {json.dumps(finviz_data_dict)}", type="text")]
# {"status": "success", "index_in_queue": query_id, "data_finviz": finviz_data_dict}


def get_crawl_status(arguments):
    """Return the crawl status stored in `CrawlInternet.QUERIES_RESULTS`.

    If the query id is not found, returns an error dict similar to the REST endpoint.

    Get this data later, after 3 minutes since you got the query_id.
    """
    query_id = arguments['query_id'] or ""
    from browser_use_impl.CrawlInternet import QUERIES_RESULTS

    if query_id in QUERIES_RESULTS: 
        return [TextContent(text= f"Te rog parseaza JSON-ul, te rog eu {QUERIES_RESULTS[query_id]}", type="text")]
    return [TextContent(text= "Te rog parseaza JSON-ul, te rog eu {\"status\": \"error\"}", type="text")]

