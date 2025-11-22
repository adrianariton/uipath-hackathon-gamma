from datetime import datetime
import os

import asyncio

from dotenv import load_dotenv

from browser_use_sdk import BrowserUse
from browser_use import ChatGoogle, ChatOpenAI, Browser, Agent, ChatBrowserUse,\
    Tools
from pydantic import BaseModel
from typing import List

import pickle

from browser_use_impl.models import FinancialOverview

load_dotenv()

llm_model = ChatOpenAI(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("GPT_URL"),
    model="google/gemini-2.5-flash-lite"
)

class DatetimeModel(BaseModel):
    year: int
    month: int
    day: int

class NewsArticle(BaseModel):
    title: str
    link: str
    is_pdf: bool
    date: DatetimeModel
    financial_overview: FinancialOverview

class NewsArticlesOutput(BaseModel):
	articles: List[NewsArticle]

def prompt(company_name: str, locations: List[str]) -> str:
    location_str = ", ".join(locations)
    if len(locations) == 0:
        location_str = "any location"
    return f"""
Search on DuckDuckGo for any official documents or any relevant news articles
about the company {company_name} that include relevant financial information,
such as earnings reports, financial statements, market analysis or governmental
reports such as Internal Revenue Service filings in the US or a similar agency
in other countries. Look for documents and news published in the last quarter,
tailoring your search to the locations: {location_str}.
Enter the links of the documents or news articles you find, and for each one,
extract the relevant financial information into a structured format as defined
in the FinancialOverview model. If a document is a PDF, make sure to download
and parse it accordingly.
Look over multiple sources (analyse at least 5 reports and give broader views over
the financial situation of the company).
When you enter DuckDuckGo, make sure to change the region settings to match
the locations provided (if any).
"""

SYSTEM_PROMPT = """
You are a financial analyst bot. You extract financial data from documents and news articles.
You have to fill in the FinancialOverview model with accurate data extracted from the documents.
Try to make for the relevant sources and fill in as much data as possible. You must only use data
that you can find in the documents, do not make up any data or use any prior knowledge.
Prioritize data from official documents over news articles. Inform from well-known
sources only (such as Reuters, Bloomberg, Financial Times, Wall Street Journal or the company itself).
Initially focus on finding official documents in PDF format and analyze them first.
If you find a PDF, download it and parse it to extract the data.
If you cannot find enough data from official documents, you can supplement it with data
from relevant news articles.
"""

async def basic_search(company_name: str, locations: List[str] = []):
	# """Simplest usage - just pass cloud params directly."""
	browser = Browser(use_cloud=False, auto_download_pdfs=True, downloads_path='./downloads',
                   accept_downloads=True)
 
	print(llm_model.model)

	agent = Agent(
		override_system_message=SYSTEM_PROMPT,
		task=prompt(company_name=company_name, locations=locations),
		llm=llm_model,
		browser=browser,
        output_model_schema=NewsArticlesOutput,
        max_failures=2,
        step_timeout=30,
        max_steps=15
	)

	history = await agent.run()
	
	with open('structured_output.json', 'w') as f:
		print(history.model_dump_json(), file=f)
	print(f'Usage: {history.usage}')
 
	print(history.structured_output)

	pickle.dump(history.structured_output, open(f'data/{company_name}_structured_output.pkl', 'wb'))

def main():
    asyncio.run(basic_search("Bending Spoons", locations=["IT"]))

if __name__ == "__main__":
    main()