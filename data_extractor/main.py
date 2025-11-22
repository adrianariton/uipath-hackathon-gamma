import asyncio
from browser_use_impl.CrawlInternet import basic_search, NewsArticlesOutput


if __name__ == "__main__":
    asyncio.run(basic_search("Domino's", locations=["RO"]))