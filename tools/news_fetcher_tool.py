"""
NewsFetcherTool
----------------
Custom CrewAI tool. Does NOT use any CrewAI built-in search tool.
Calls SerperDev's News API directly over HTTP (httpx), falling back to NewsAPI.org
if SERPER_API_KEY isn't set. Both have free tiers.

Dedup happens HERE, inside the tool, rather than as a separate tool call the
agent has to remember to make -- small/fast models routinely stop after one
successful tool call and skip a second one, so filtering can't depend on the
LLM's judgment. This way every fetch is automatically deduped against the
Sheet's recent headlines, no matter what the agent does.
"""
import httpx
from datetime import datetime, timezone
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Type

from config import config
from tools.sheets_tool import get_recent_headlines, _normalize_headline


class NewsFetcherInput(BaseModel):
    topics: List[str] = Field(..., description="List of topics to search headlines for, e.g. ['AI', 'crypto']")
    max_per_topic: int = Field(8, description="Max headlines to pull per topic")


class NewsFetcherTool(BaseTool):
    name: str = "news_fetcher"
    description: str = (
        "Fetches the latest news headlines for a list of topics, automatically "
        "excluding anything already logged to the Sheet recently. "
        "Returns a list of dicts with title, source, url, published_at, topic."
    )
    args_schema: Type[BaseModel] = NewsFetcherInput

    def _run(self, topics: List[str], max_per_topic: int = 8) -> List[dict]:
        if config.MAX_PER_TOPIC:
            max_per_topic = min(max_per_topic, config.MAX_PER_TOPIC)

        if config.SERPER_API_KEY:
            results = self._fetch_serper(topics, max_per_topic)
        elif config.NEWSAPI_API_KEY:
            results = self._fetch_newsapi(topics, max_per_topic)
        else:
            raise RuntimeError("No SERPER_API_KEY or NEWSAPI_API_KEY configured.")

        return self._filter_duplicates(results)

    def _filter_duplicates(self, articles: List[dict]) -> List[dict]:
        """Drops any article whose headline was already logged recently.
        Headline-based, not URL-based, because aggregator source links
        (e.g. Google News redirects) can vary per fetch even for the exact
        same story -- but the Guardian/direct-source case you hit shows
        even IDENTICAL URLs can get through if this check doesn't run at
        all, which is the actual bug this fixes."""
        recent_headlines = get_recent_headlines()
        new_articles = [
            a for a in articles
            if _normalize_headline(a.get("title", "")) not in recent_headlines
        ]
        return new_articles

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