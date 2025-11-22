from datetime import datetime
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
import asyncio

from dotenv import load_dotenv

from browser_use_sdk import BrowserUse
from browser_use import BrowserSession, ChatGoogle, ChatOpenAI, Browser, Agent, ChatBrowserUse,\
    Tools
from pydantic import BaseModel
from typing import List

# import pickle

try:
    from .models import FinancialOverview, SimpleNewsOutput, SimpleFinancialData
except ImportError:
    # Fallback for running as standalone script
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from models import FinancialOverview, SimpleNewsOutput, SimpleFinancialData

load_dotenv()

llm_model = ChatOpenAI(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("GPT_URL"),
    model="google/gemini-2.5-pro"
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
Extract key financial information and organize it in a simple, structured format.
Focus on finding:
1. Revenue/income figures
2. Profit/earnings data  
3. Employee count
4. Key financial highlights

Only include data you can find in the documents - do not make up any information.
Prioritize official documents and well-known financial news sources.
For each article/document, provide a brief summary of the financial content.
If you find PDFs, download and analyze them for financial data.
"""

# query_id -> {result: json from pydantic, status: "in_progress"|"done"}
GLOBAL_CNT = 0
QUERIES_RESULTS = {}

# Thread pool executor for background tasks
THREAD_POOL = ThreadPoolExecutor(max_workers=10)
TASK_LOCK = threading.Lock()

def _run_browser_task(query_id: int, company_name: str, locations: List[str]):
	"""Background task that runs the browser automation."""
	try:
		# Create new event loop for this thread
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		
		browser = Browser(use_cloud=False, auto_download_pdfs=True, downloads_path='./downloads',
		                 accept_downloads=True)
		
		print(f"[Thread {query_id}] Starting browser automation for {company_name}")
		print(f"[Thread {query_id}] Model: {llm_model.model}")

		# Use browser from browserless on port 3001
		# browser = BrowserSession(
		# 	cdp_url="ws://localhost:3001/"
		# )
  
		agent = Agent(
			override_system_message=SYSTEM_PROMPT,
			task=prompt(company_name=company_name, locations=locations),
			llm=llm_model,
			browser=browser,
			output_model_schema=SimpleNewsOutput,
			max_failures=4,
			step_timeout=30,
			max_steps=30,
			llm_timeout=120,
			# browser_session=browser
		)

		# Run the agent
		history = loop.run_until_complete(agent.run())
		
		# Update results with thread safety
		with TASK_LOCK:
			QUERIES_RESULTS[query_id]["result"] = history.structured_output.model_dump_json()
			QUERIES_RESULTS[query_id]["status"] = "done"

		print(f'[Thread {query_id}] Usage: {history.usage}')
		
		# Ensure data directory exists
		os.makedirs('./data', exist_ok=True)
		
		# Save structured output as json
		with open(f'./data/{company_name}_structured_output.json', 'w') as f:
			f.write(history.structured_output.model_dump_json())
			
		print(f'[Thread {query_id}] Completed browser automation for {company_name}')
		
	except Exception as e:
		print(f'[Thread {query_id}] Error in browser task: {str(e)}')
		with TASK_LOCK:
			QUERIES_RESULTS[query_id]["status"] = "error"
			QUERIES_RESULTS[query_id]["result"] = f"Error: {str(e)}"
	finally:
		if 'loop' in locals():
			loop.close()

async def basic_search(company_name: str, locations: List[str] = []):
	"""Main search function that checks cache and queues browser tasks."""
	global GLOBAL_CNT
	
	# First, verify if JSON file exists
	json_file_path = f'./data/{company_name}_structured_output.json'
	if os.path.exists(json_file_path):
		print(f'Loading existing structured output for {company_name}...')
		try:
			with open(json_file_path, 'r') as f:
				structured_output = f.read()
			print(f'Loaded cached data for {company_name}')
			
			with TASK_LOCK:
				current_cnt = GLOBAL_CNT
				GLOBAL_CNT += 1
				QUERIES_RESULTS[current_cnt] = {"status": "done", "result": structured_output}
			
			yield current_cnt
			return
		except Exception as e:
			print(f'Error loading cached data for {company_name}: {str(e)}')
			# Continue to create new task if cache loading fails
	
	# If file doesn't exist, queue browser task in background thread
	with TASK_LOCK:
		current_cnt = GLOBAL_CNT
		GLOBAL_CNT += 1
		QUERIES_RESULTS[current_cnt] = {"status": "in_progress", "result": None}
	
	# Submit task to thread pool
	future = THREAD_POOL.submit(_run_browser_task, current_cnt, company_name, locations)
	print(f'Queued browser task {current_cnt} for {company_name} in background thread')
	
	# Yield the query ID immediately so other operations can continue
	yield current_cnt

async def main():
    params = [
        	# ("Microsoft", ["US"]), ("UiPath", None),
         ("Databricks", ["DE", "US", "NL"])]

    for _company_name, locations in params:
        async for query_id in basic_search(_company_name, locations=locations):
            print(f"Query ID: {query_id}")

            # Demonstrate that other operations can continue while browser task runs
            print("Other operations can continue while browser task runs in background...")

            # Poll status periodically
            for i in range(30):  # Check for 150 seconds
                await asyncio.sleep(5)
                status = get_query_status(query_id)
            print(f"Status check {i+1}: {status['status']}")
            if status['status'] in ['done', 'error']:
                print(f"Task completed with status: {status['status']}")
                if status['status'] == 'done':
                    print("Result available in QUERIES_RESULTS")
                break
        
        # Cleanup
        # cleanup_thread_pool()

def get_query_status(query_id: int) -> dict:
	"""Get the status of a specific query."""
	with TASK_LOCK:
		return QUERIES_RESULTS.get(query_id, {"status": "not_found", "result": None})

def get_all_queries() -> dict:
	"""Get status of all queries."""
	with TASK_LOCK:
		return QUERIES_RESULTS.copy()

def cleanup_thread_pool():
	"""Cleanup the thread pool executor."""
	THREAD_POOL.shutdown(wait=True)
	print("Thread pool cleaned up")

if __name__ == "__main__":
    asyncio.run(main())