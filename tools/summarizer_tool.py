"""
SummarizerTool
--------------
Custom tool that calls Groq's OpenAI-compatible chat completions endpoint
directly via httpx (no CrewAI built-in LLM tool wrapper) to turn a fetched
article into a short, clear, factual update.

Groq's on-demand tier enforces a low tokens-per-minute (TPM) cap per model,
shared across every call in a run. To stay under it without crashing the
pipeline, this tool:
  1. Sleeps SUMMARY_DELAY_SECONDS between calls, spreading usage out instead
     of bursting it.
  2. On a 429 rate-limit response, reads Groq's "try again in Xs" hint (or
     the Retry-After header) and waits that long before retrying, instead of
     failing immediately.
"""
import re
import time
from typing import Type
import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from config import config

# config.LLM_MODEL is "groq/openai/gpt-oss-20b" (LiteLLM-style provider
# prefix); Groq's own REST endpoint wants just the bare model id, so strip
# the leading "groq/" here.
_MODEL_NAME = config.LLM_MODEL.split("/", 1)[-1] if config.LLM_MODEL.startswith("groq/") else config.LLM_MODEL
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_RETRY_SECONDS_RE = re.compile(r"try again in ([\d.]+)s", re.IGNORECASE)
_MAX_RETRIES = 10


class SummarizerInput(BaseModel):
    title: str = Field(..., description="Article headline")
    source: str = Field("", description="Publication/source name")
    url: str = Field("", description="Article URL")


class SummarizerTool(BaseTool):
    name: str = "summarize_article"
    description: str = (
        "Summarizes a fetched article into a short, clear, factual 2-3 sentence "
        "update. Returns {summary}."
    )
    args_schema: Type[BaseModel] = SummarizerInput

    def _run(self, title: str, source: str = "", url: str = "") -> dict:
        prompt = (
            "You are a precise news editor. Given this headline, write a neutral, "
            "factual 2-3 sentence update a reader could skim in a Slack message. "
            "Do not invent facts not implied by the headline. Do not editorialize.\n\n"
            f"Headline: {title}\n"
            f"Source: {source or 'unknown'}\n\n"
            "Respond with ONLY the summary text, no preamble."
        )
        summary = self._call_with_backoff(prompt)

        # Throttle so back-to-back calls don't burst past the TPM window.
        if config.SUMMARY_DELAY_SECONDS > 0:
            time.sleep(config.SUMMARY_DELAY_SECONDS)

        return {"summary": summary}

    def _call_with_backoff(self, prompt: str) -> str:
        last_error = None
        for attempt in range(_MAX_RETRIES):
            try:
                with httpx.Client(timeout=30) as client:
                    resp = client.post(
                        GROQ_URL,
                        headers={
                            "Authorization": f"Bearer {config.GROQ_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": _MODEL_NAME,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.3,
                            "max_tokens": 150,
                        },
                    )
                if resp.status_code == 429:
                    wait_s = self._parse_retry_wait(resp)
                    print(
                        f"\n[SummarizerTool] Groq 429 RateLimit (attempt {attempt + 1}/{_MAX_RETRIES}). "
                        f"Sleeping {wait_s:.1f}s..."
                    )
                    time.sleep(wait_s)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    wait_s = self._parse_retry_wait(e.response)
                    print(
                        f"\n[SummarizerTool] Groq 429 RateLimit (attempt {attempt + 1}/{_MAX_RETRIES}). "
                        f"Sleeping {wait_s:.1f}s..."
                    )
                    time.sleep(wait_s)
                    continue
                raise

        raise RuntimeError(
            f"Groq rate limit persisted after {_MAX_RETRIES} retries"
        ) from last_error

    @staticmethod
    def _parse_retry_wait(response: httpx.Response) -> float:
        # Prefer the standard Retry-After header if Groq sends one.
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return float(retry_after) + 0.5
            except ValueError:
                pass
        # Otherwise parse Groq's "Please try again in 12.17s" from the body.
        try:
            match = _RETRY_SECONDS_RE.search(response.text)
            if match:
                return float(match.group(1)) + 0.5
        except Exception:
            pass
        return 5.0