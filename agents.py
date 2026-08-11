"""
Defines the 4 agents, one per tool. All reasoning goes through Groq via
LiteLLM, which CrewAI uses natively — set with the `llm` string, no extra
wrapper needed. Tools are all custom (see tools/), never CrewAI's built-in
tool set.
"""
import re
import time
from crewai import Agent
import litellm

# Configure LiteLLM retries & timeout
litellm.num_retries = 10
litellm.request_timeout = 120

# Wrap litellm.completion to catch Groq rate limit (TPM/RPM 429) errors, parse
# Groq's wait time hint ("try again in Xs"), and wait automatically.
_RETRY_SECONDS_RE = re.compile(r"try again in ([\d.]+)s", re.IGNORECASE)
_original_completion = litellm.completion


def completion_with_rate_limit_handling(*args, **kwargs):
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            return _original_completion(*args, **kwargs)
        except (litellm.exceptions.RateLimitError, Exception) as e:
            err_msg = str(e)
            is_rate_limit = (
                isinstance(e, litellm.exceptions.RateLimitError)
                or "rate_limit" in err_msg.lower()
                or "429" in err_msg
            )
            if not is_rate_limit or attempt == max_attempts - 1:
                raise

            match = _RETRY_SECONDS_RE.search(err_msg)
            if match:
                wait_s = float(match.group(1)) + 2.0
            else:
                wait_s = min(60.0, (2 ** attempt) * 4.0 + 5.0)

            print(
                f"\n[LiteLLM RateLimit] Groq limit reached (attempt {attempt + 1}/{max_attempts}). "
                f"Sleeping {wait_s:.1f}s before retrying..."
            )
            time.sleep(wait_s)


litellm.completion = completion_with_rate_limit_handling

from config import config
from tools.news_fetcher_tool import NewsFetcherTool
from tools.summarizer_tool import SummarizerTool
from tools.slack_tool import SlackBotTool
from tools.sheets_tool import SheetsLoggerTool

LLM = config.LLM_MODEL  # e.g. "groq/openai/gpt-oss-20b"


def build_agents():
    news_fetcher_agent = Agent(
        role="News Fetcher",
        goal=(
            "Pull the freshest, most relevant headlines for EXACTLY the topic list given "
            "in the current task -- never substitute a default or previously-used topic "
            "list. The topics to search are whatever the task says, every single run."
        ),
        backstory=(
            "A wire-service scanner that never sleeps, and never assumes it already knows "
            "the beat. Each shift hands it a fresh topic list, and it searches only that "
            "list -- never its own memory of past assignments. Cares only about recency "
            "and relevance to the topics it was just given."
        ),
        tools=[NewsFetcherTool()],
        llm=LLM,
        max_rpm=config.MAX_RPM,
        verbose=True,
    )

    summarizer_agent = Agent(
        role="Summarizer",
        goal="Turn each fetched article into one clear, neutral, factual 2-3 sentence update.",
        backstory=(
            "A former beat reporter who can compress a headline into a tight, "
            "accurate summary without adding a single fact that wasn't there."
        ),
        tools=[SummarizerTool()],
        llm=LLM,
        max_rpm=config.MAX_RPM,
        verbose=True,
    )

    publisher_agent = Agent(
        role="Publisher",
        goal="Post every headline + summary + link to the configured Slack channel.",
        backstory="Owns the gate between the newsroom and the reader's Slack sidebar.",
        tools=[SlackBotTool()],
        llm=LLM,
        max_rpm=config.MAX_RPM,
        verbose=True,
    )

    logger_agent = Agent(
        role="Logger",
        goal="Log every published story to the Google Sheet for record-keeping.",
        backstory="The paper trail. If it isn't in the Sheet, it didn't happen.",
        tools=[SheetsLoggerTool()],
        llm=LLM,
        max_rpm=config.MAX_RPM,
        verbose=True,
    )

    return {
        "news_fetcher": news_fetcher_agent,
        "summarizer": summarizer_agent,
        "publisher": publisher_agent,
        "logger": logger_agent,
    }