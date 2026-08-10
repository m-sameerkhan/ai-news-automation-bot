"""
SlackBotTool
------------
Custom tool that posts to a Slack Incoming Webhook via a plain HTTP POST
(httpx). No Slack SDK, no CrewAI built-in Slack tool. Webhook is already
scoped to one private channel, so no bot token/OAuth is required.
"""
from typing import List, Type
import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from config import config


class SlackPostInput(BaseModel):
    headline: str = Field(..., description="Story headline")
    summary: str = Field(..., description="2-3 sentence summary")
    source_urls: List[str] = Field(..., description="One or more source article URLs")
    update_tag: str = Field("", description="Optional 'Update on: ...' tag if this is a follow-up story")


class SlackBotTool(BaseTool):
    name: str = "post_to_slack"
    description: str = (
        "Posts a formatted news card to the configured private Slack channel via "
        "an incoming webhook. Format: headline, summary, then one link per source."
    )
    args_schema: Type[BaseModel] = SlackPostInput

    def _run(self, headline: str, summary: str, source_urls: List[str], update_tag: str = "") -> dict:
        if not config.SLACK_WEBHOOK_URL:
            raise RuntimeError("SLACK_WEBHOOK_URL is not configured.")

        lines = [f"📰 *{headline}*", summary]
        if update_tag:
            lines.append(f"_Update on: {update_tag}_")
        for url in source_urls:
            lines.append(f"🔗 <{url}|Read full article>")

        text = "\n".join(lines)

        with httpx.Client(timeout=15) as client:
            resp = client.post(config.SLACK_WEBHOOK_URL, json={"text": text})
            resp.raise_for_status()

        return {"posted": True, "channel_text": text}