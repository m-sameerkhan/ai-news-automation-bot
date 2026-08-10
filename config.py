"""Central place to read env vars. Keeps tools/agents free of os.environ calls."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
    NEWSAPI_API_KEY = os.environ.get("NEWSAPI_API_KEY", "")

    SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

    GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    GOOGLE_SERVICE_ACCOUNT_PATH = os.environ.get("GOOGLE_SERVICE_ACCOUNT_PATH", "")
    GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")

    # Groq's free/on-demand tier has a low tokens-per-minute (TPM) cap per
    # model (e.g. 8000 TPM for openai/gpt-oss-20b), shared across every agent
    # reasoning step AND every SummarizerTool call in a run. Keep these small
    # unless you're on a paid Dev Tier — see SUMMARY_DELAY_SECONDS below.
    NEWS_TOPICS = [t.strip() for t in os.environ.get("NEWS_TOPICS", "AI,tech").split(",") if t.strip()]
    MAX_PER_TOPIC = int(os.environ.get("MAX_PER_TOPIC", "3"))

    # Maximum LLM Requests Per Minute per agent (helps stay within Groq TPM caps)
    MAX_RPM = int(os.environ.get("MAX_RPM", "3"))

    # llama-3.3-70b-versatile was deprecated by Groq in June 2026. Google's
    # recommended replacement for general-purpose/agentic work is
    # openai/gpt-oss-20b (fast/cheap) or openai/gpt-oss-120b (stronger).
    # "groq/" prefix is LiteLLM's provider routing, used by the CrewAI agents;
    # the SummarizerTool calls Groq's REST API directly and strips the prefix.
    LLM_MODEL = os.environ.get("LLM_MODEL", "groq/openai/gpt-oss-20b")

    # Seconds to sleep between SummarizerTool calls, to spread token usage
    # across the TPM window instead of bursting it. Raise this (or lower
    # MAX_PER_TOPIC / NEWS_TOPICS) if you're still hitting rate limits.
    SUMMARY_DELAY_SECONDS = float(os.environ.get("SUMMARY_DELAY_SECONDS", "5"))

    SHEET_TAB = "news_log"


config = Config()