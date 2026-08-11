"""
SheetsLoggerTool
-----------------
Custom tool wrapping the Google Sheets API directly via a service account
(gspread + google-auth), no CrewAI built-in tool. Appends one row per
published story so the Sheet is a simple, append-only record of everything
the bot has posted.

Sheet columns (single tab): date | topic | headline | summary | source_urls

Dedup is headline-based, not URL-based -- aggregator source links (Google
News redirects, etc.) can vary per fetch even for the same story, and
relying on an LLM agent to remember to call a separate dedup tool proved
unreliable, so filtering now happens deterministically inside
NewsFetcherTool itself, using get_recent_headlines() below.
"""
import json
import re
from datetime import datetime, timezone, timedelta
from typing import List, Type, Set
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from config import config

COLUMNS = ["date", "topic", "headline", "summary", "source_urls"]


_client = None
_sheet = None


def _get_sheet():
    """Lazily authenticate and open the worksheet, reused across warm invocations."""
    global _client, _sheet
    if _sheet is not None:
        return _sheet

    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    if config.GOOGLE_SERVICE_ACCOUNT_PATH:
        creds = Credentials.from_service_account_file(config.GOOGLE_SERVICE_ACCOUNT_PATH, scopes=scopes)
    elif config.GOOGLE_SERVICE_ACCOUNT_JSON:
        info = json.loads(config.GOOGLE_SERVICE_ACCOUNT_JSON)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
    else:
        raise RuntimeError(
            "Set either GOOGLE_SERVICE_ACCOUNT_PATH (path to the JSON key file) "
            "or GOOGLE_SERVICE_ACCOUNT_JSON (its full contents) in your .env."
        )

    if not config.GOOGLE_SHEET_ID:
        raise RuntimeError("GOOGLE_SHEET_ID not configured.")

    _client = gspread.authorize(creds)

    spreadsheet = _client.open_by_key(config.GOOGLE_SHEET_ID)
    try:
        _sheet = spreadsheet.worksheet(config.SHEET_TAB)
    except Exception:
        _sheet = spreadsheet.add_worksheet(title=config.SHEET_TAB, rows=2000, cols=len(COLUMNS))
        _sheet.append_row(COLUMNS)
    return _sheet


def _dedup_window_hours() -> int:
    return config.DEDUP_WINDOW_HOURS


def _normalize_headline(headline: str) -> str:
    """Lowercase, strip punctuation/extra whitespace so near-identical
    headlines match even with minor formatting differences between fetches."""
    h = headline.lower().strip()
    h = re.sub(r"[^\w\s]", "", h)
    h = re.sub(r"\s+", " ", h)
    return h


def get_recent_headlines(hours: int = None) -> Set[str]:
    """
    Returns a set of normalized headlines logged within the last `hours`
    (defaults to DEDUP_WINDOW_HOURS / 48h). Called from NewsFetcherTool
    before returning results, so duplicate stories never reach the
    summarizer, publisher, or logger agents.
    """
    if hours is None:
        hours = _dedup_window_hours()

    sheet = _get_sheet()
    records = sheet.get_all_records()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    headlines: Set[str] = set()
    for r in records:
        raw_date = str(r.get("date", ""))
        if not raw_date:
            continue
        try:
            dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if dt < cutoff:
            continue
        h = str(r.get("headline", ""))
        if h:
            headlines.add(_normalize_headline(h))
    return headlines


def is_duplicate_article(headline: str, hours: int = None) -> bool:
    """True if this headline (normalized) was already logged within the
    dedup window. Used as a final safety net in SheetsLoggerTool."""
    recent = get_recent_headlines(hours=hours)
    return _normalize_headline(headline) in recent


class LogSummaryInput(BaseModel):
    topic: str = Field(..., description="Topic the story was fetched under, e.g. 'AI'")
    headline: str = Field(..., description="Story headline")
    summary: str = Field(..., description="Short, clear summary of the story")
    source_urls: List[str] = Field(..., description="One or more source article URLs")


class SheetsLoggerTool(BaseTool):
    name: str = "log_to_sheet"
    description: str = (
        "Appends a row to the Google Sheet with date, topic, headline, summary, "
        "and source links, for record-keeping of every story processed. "
        "Skips silently if the headline was already logged recently."
    )
    args_schema: Type[BaseModel] = LogSummaryInput

    def _run(self, topic: str, headline: str, summary: str, source_urls: List[str]) -> dict:
        # Safety net: even though NewsFetcherTool now filters duplicates
        # before summarization, never write a duplicate row regardless of
        # how an article got this far.
        if is_duplicate_article(headline):
            return {"written": False, "headline": headline, "reason": "duplicate_headline"}

        sheet = _get_sheet()
        row = [
            datetime.now(timezone.utc).isoformat(),
            topic,
            headline,
            summary,
            "|".join(source_urls),
        ]
        sheet.append_row(row)
        return {"written": True, "headline": headline}


def read_recent_stories(limit: int = 30) -> List[dict]:
    """
    Read-only helper for the dashboard feed -- NOT a CrewAI tool, just a plain
    function the API endpoint calls directly. Returns the most recently
    logged stories, newest first, reusing the same authenticated worksheet
    connection as the logger above.
    """
    sheet = _get_sheet()
    records = sheet.get_all_records()
    records = records[-limit:]
    records.reverse()

    items = []
    for r in records:
        raw_sources = str(r.get("source_urls", ""))
        items.append({
            "date": r.get("date", ""),
            "topic": r.get("topic", ""),
            "headline": r.get("headline", ""),
            "summary": r.get("summary", ""),
            "source_urls": [u for u in raw_sources.split("|") if u],
        })
    return items