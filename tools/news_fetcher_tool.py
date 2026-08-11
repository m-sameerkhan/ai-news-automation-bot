"""
NewsFetcherTool
----------------
Custom CrewAI tool. Does NOT use any CrewAI built-in search tool.
Calls SerperDev's News API directly over HTTP (httpx), falling back to NewsAPI.org
if SERPER_API_KEY isn't set. Both have free tiers.
"""
import httpx
from datetime import datetime, timezone
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Type

from config import config


class NewsFetcherInput(BaseModel):
    topics: List[str] = Field(..., description="List of topics to search headlines for, e.g. ['AI', 'crypto']")
    max_per_topic: int = Field(8, description="Max headlines to pull per topic")


class NewsFetcherTool(BaseTool):
    name: str = "news_fetcher"
    description: str = (
        "Fetches the latest news headlines for a list of topics. "
        "Returns a list of dicts with title, source, url, published_at, topic."
    )
    args_schema: Type[BaseModel] = NewsFetcherInput

    def _run(self, topics: List[str], max_per_topic: int = 8) -> List[dict]:
        # Don't trust the agent's tool call to actually respect the
        # MAX_PER_TOPIC instruction in the task description -- that's just
        # prose, and smaller/faster models routinely ignore numeric
        # constraints that only live in text. Enforce a hard ceiling here
        # instead, so your .env setting is always the real limit no matter
        # what value the LLM decides to pass.
        if config.MAX_PER_TOPIC:
            max_per_topic = min(max_per_topic, config.MAX_PER_TOPIC)

        if config.SERPER_API_KEY:
            return self._fetch_serper(topics, max_per_topic)
        if config.NEWSAPI_API_KEY:
            return self._fetch_newsapi(topics, max_per_topic)
        raise RuntimeError("No SERPER_API_KEY or NEWSAPI_API_KEY configured.")

    def _fetch_serper(self, topics: List[str], max_per_topic: int) -> List[dict]:
        results = []
        with httpx.Client(timeout=15) as client:
            for topic in topics:
                resp = client.post(
                    "https://google.serper.dev/news",
                    headers={"X-API-KEY": config.SERPER_API_KEY, "Content-Type": "application/json"},
                    json={"q": topic, "num": max_per_topic},
                )
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("news", [])[:max_per_topic]:
                    results.append({
                        "title": item.get("title", ""),
                        "source": item.get("source", ""),
                        "url": item.get("link", ""),
                        "published_at": item.get("date", ""),
                        "topic": topic,
                    })
        return results

    def _fetch_newsapi(self, topics: List[str], max_per_topic: int) -> List[dict]:
        results = []
        with httpx.Client(timeout=15) as client:
            for topic in topics:
                resp = client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": topic,
                        "pageSize": max_per_topic,
                        "sortBy": "publishedAt",
                        "language": "en",
                        "apiKey": config.NEWSAPI_API_KEY,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("articles", [])[:max_per_topic]:
                    results.append({
                        "title": item.get("title", ""),
                        "source": (item.get("source") or {}).get("name", ""),
                        "url": item.get("url", ""),
                        "published_at": item.get("publishedAt", datetime.now(timezone.utc).isoformat()),
                        "topic": topic,
                    })
        return results