"""
SheetsLoggerTool
-----------------
Custom tool wrapping the Google Sheets API directly via a service account
(gspread + google-auth), no CrewAI built-in tool. Appends one row per
published story so the Sheet is a simple, append-only record of everything
the bot has posted.

Sheet columns (single tab): date | topic | headline | summary | source_urls
"""
import json
from datetime import datetime, timezone
from typing import List, Type
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
        # Local/dev-friendly: a path to the service account JSON key file.
        creds = Credentials.from_service_account_file(config.GOOGLE_SERVICE_ACCOUNT_PATH, scopes=scopes)
    elif config.GOOGLE_SERVICE_ACCOUNT_JSON:
        # CI/serverless-friendly: the full JSON contents as a single env var.
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


class LogSummaryInput(BaseModel):
    topic: str = Field(..., description="Topic the story was fetched under, e.g. 'AI'")
    headline: str = Field(..., description="Story headline")
    summary: str = Field(..., description="Short, clear summary of the story")
    source_urls: List[str] = Field(..., description="One or more source article URLs")


class SheetsLoggerTool(BaseTool):
    name: str = "log_to_sheet"
    description: str = (
        "Appends a row to the Google Sheet with date, topic, headline, summary, "
        "and source links, for record-keeping of every story processed."
    )
    args_schema: Type[BaseModel] = LogSummaryInput

    def _run(self, topic: str, headline: str, summary: str, source_urls: List[str]) -> dict:
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