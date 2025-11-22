#!/usr/bin/env python3
"""Example runner for the browser-use crawl integration.

This script demonstrates calling the `start_crawl` implementation directly
from the `excel_mcp` package. It checks for required environment variables
and exits gracefully if they are not present so it can be run safely in CI
or developer machines without secrets configured.
"""
import os
import sys
import asyncio

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# Add repo root and package src to sys.path so both `data_extractor` and
# `excel_mcp` can be imported when running this example from the examples dir.
SRC = os.path.join(ROOT, "excel-mcp-server", "src")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from excel_mcp.browser_use_client import start_crawl as start_crawl_impl, get_crawl_status as get_crawl_status_impl


async def main():
    api_key = os.environ.get("API_KEY")
    if not api_key:
        print("API_KEY not set. Example will not perform network calls.")
        print("To run fully, set API_KEY and GPT_URL in your environment.")
        return

    prompt = "Analyze Tesla's financials and list key official documents and recent news."
    print("Starting crawl example with prompt:\n", prompt)
    try:
        res = await start_crawl_impl(prompt=prompt, company_name=None, locations=["US"])
        print("Result:\n", res)

        query_id = res.get("index_in_queue")
        if query_id is None:
            print("No browser job was enqueued (index_in_queue is None). If you expect browser processing, ensure Playwright/browser-use is installed and available.")
            return

        # Poll for status until done or timeout
        timeout_seconds = 600
        poll_interval = 5
        waited = 0
        print(f"Polling status for query id {query_id}... (timeout {timeout_seconds}s)")
        while waited < timeout_seconds:
            status = get_crawl_status_impl(query_id)
            print(f"Status at {waited}s: {status.get('status')}")
            if status.get("status") == "done":
                print("Browser agent finished. Result:")
                print(status.get("result"))
                break
            await asyncio.sleep(poll_interval)
            waited += poll_interval
        else:
            print(f"Timed out waiting for query {query_id} after {timeout_seconds} seconds")
    except Exception as e:
        print("Example failed:", e)


if __name__ == "__main__":
    asyncio.run(main())
