from datetime import datetime
import os

import asyncio

from dotenv import load_dotenv

from browser_use_sdk import BrowserUse
from browser_use import ChatOpenAI, Browser, Agent, ChatBrowserUse
from pydantic import BaseModel
from typing import List

load_dotenv()

llm_model = ChatOpenAI(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("GPT_URL"),
    model="google/gemini-2.5-flash-lite"
)

class NewsArticle(BaseModel):
    title: str
    link: str
    date: datetime

async def basic():
	"""Simplest usage - just pass cloud params directly."""
	browser = Browser(use_cloud=False)

	agent = Agent(
		task='Give me links to top 5 news articles\
            about Meta in Canada in the last quarter.',
		llm=llm_model,
		browser=browser,
        output_model_schema=List[NewsArticle],
        max_failures=2
	)

	result = await agent.run()
	print(f"Top 5 news articles about Meta in Canada	 in the last quarter: {result.model_dump_json()}", file=open('result.txt', 'w'))
	print(f'Usage: {result.usage}')

def main():
    asyncio.run(basic())
	
if __name__ == "__main__":
    main()