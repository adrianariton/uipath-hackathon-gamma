import httpx
import asyncio

from dotenv import load_dotenv
import os
load_dotenv()

GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')  # free API key from https://gnews.io/

async def get_latest_news(query: str, max_results: int = 5) -> list[list[str]]:
    """
    Fetch the most recent news articles for a given query using the GNews API.
    """
    url = "https://gnews.io/api/v4/search"
    api_key = GNEWS_API_KEY  # free API key from https://gnews.io/
    params = {
        "q": query,
        "lang": "en",
        "max": max_results,
        "apikey": api_key
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    
    news_list = []
    for article in data.get("articles", []):
        news_list.append({
            "title": article["title"],
            "description": article.get("description"),
            "url": article["url"],
            "published_at": article["publishedAt"],
            "source": article["source"]["name"]
        })

    # convert the news_list to a list[[]] static the columns: Title, Description, URL, Published At, Source
    news_matrix = [["Title", "Description", "URL", "Published At", "Source"]]
    for news in news_list:
        news_matrix.append([
            news["title"],
            news["description"],
            news["url"],
            news["published_at"],
            news["source"]
        ])

    return news_matrix
