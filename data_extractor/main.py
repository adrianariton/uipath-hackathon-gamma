# Make a server that accepts requests to crawl the internet for financial data
import asyncio
import os
from dotenv import load_dotenv
from typing import Optional, List

from browser_use_impl.CrawlInternet import basic_search, QUERIES_RESULTS
from finviz.entity_extractor import EntityExtractor, ExtractionResponse
from finviz.financial_data import FinvizScraper, TickerData

load_dotenv()

from flask import Flask, request, jsonify

app = Flask(__name__)

async def basic(company_name: str, locations: List[str] = []):
    async for query_id in basic_search(company_name, locations):
        return query_id

"""POST route to crawl the internet for financial data about a company.
    Expects a JSON body with the following structure:
    {
        "company_name": Optional[str] # "Name of the company to search for",
        "locations": Optional[List[str]] # ["List", "of", "locations"] // optional
        "prompt": str # "The prompt describing the companies/context to analyze."
    }

    Returns:
        _type_: _description_
    """
@app.route("/crawl", methods=["POST"])
def crawl():
    data = request.json
    company_name: Optional[str] = data.get("company_name", None)
    locations: Optional[List[str]] = data.get("locations", [])
    prompt: Optional[str] = data.get("prompt", None)
    
    extractionResponse : ExtractionResponse = EntityExtractor().extract(prompt)
    tickers = extractionResponse.tickers
    companies = extractionResponse.companies
    
    if company_name is None and len(companies) > 0:
        company_name = companies[0]

    query_id = asyncio.run(basic(company_name, locations))
    
    print(f"Extracted tickers: {tickers}, companies: {companies}")
    print(f"Query ID: {query_id}")
    finviz_scraper = FinvizScraper()
    finviz_data: dict[str, TickerData] = \
        finviz_scraper.get_data(tickers, top_k=10, history_limit=90)

    # Convert Pydantic models to dictionaries for JSON serialization
    finviz_data_dict = {ticker: data.model_dump() for ticker, data in finviz_data.items()}
    
    return jsonify({"status": "success", "index_in_queue": query_id,
                    "data_finviz": finviz_data_dict})

@app.route("/status/<int:query_id>", methods=["GET"])
def status(query_id: int):
    # Check the status of the query with the given ID
    if query_id in QUERIES_RESULTS:
        return jsonify(QUERIES_RESULTS[query_id])
    return jsonify({"status": "error", "message": "Query not found"}), 404

if __name__ == "__main__":
    app.run(port=8000)