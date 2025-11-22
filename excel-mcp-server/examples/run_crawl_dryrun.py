#!/usr/bin/env python3
"""Dry-run example for the browser-use crawl integration.

This script injects lightweight stub modules for the parts of
`data_extractor` that perform network I/O (LLM, browser, Finviz), then
imports and runs `start_crawl` from `excel_mcp.browser_use_client` so we can
exercise the glue code without secrets or external network access.
"""
import sys
import os
import types
import asyncio
from types import SimpleNamespace

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

def make_stubs():
    # Stub: data_extractor.finviz.entity_extractor
    mod_ent = types.ModuleType("data_extractor.finviz.entity_extractor")
    class StubExtractor:
        def extract(self, prompt: str):
            return SimpleNamespace(tickers=["TSLA"], companies=["Tesla"], context=["2025"])
    mod_ent.EntityExtractor = StubExtractor
    sys.modules["data_extractor.finviz.entity_extractor"] = mod_ent

    # Stub: data_extractor.finviz.financial_data
    mod_fin = types.ModuleType("data_extractor.finviz.financial_data")
    class StubTickerData:
        def __init__(self, payload):
            self._payload = payload
        def model_dump(self):
            return self._payload
    class StubFinviz:
        def get_data(self, tickers, top_k=10, history_limit=90):
            return {t: StubTickerData({"news":[], "metrics":{"PE":"100"}, "historical":[]}) for t in tickers}
    mod_fin.FinvizScraper = StubFinviz
    sys.modules["data_extractor.finviz.financial_data"] = mod_fin

    # Stub: data_extractor.browser_use_impl.CrawlInternet
    mod_crawl = types.ModuleType("data_extractor.browser_use_impl.CrawlInternet")
    async def basic_search(company_name: str, locations: list = []):
        # yield a fake queue id immediately, then simulate finishing later
        yield 42
    mod_crawl.basic_search = basic_search
    mod_crawl.QUERIES_RESULTS = {42: {"status":"done","result":{"stub":"ok"}}}
    sys.modules["data_extractor.browser_use_impl.CrawlInternet"] = mod_crawl

def run_dry():
    make_stubs()
    from excel_mcp.browser_use_client import start_crawl as start_crawl_impl, get_crawl_status as get_crawl_status_impl

    async def do():
        print("Calling start_crawl (dry-run)…")
        res = await start_crawl_impl(prompt="Dry run: test Tesla", company_name=None, locations=["US"])
        print("start_crawl returned:")
        print(res)

        print('\nChecking crawl status for id 42:')
        status = get_crawl_status_impl(42)
        print(status)

    asyncio.run(do())

if __name__ == "__main__":
    run_dry()
