"""
Task definitions for the single linear pipeline: fetch -> summarize -> post to
Slack -> log to Sheet. All four run in one Crew, one process.
"""
from crewai import Task

from config import config


def build_tasks(agents: dict):
    fetch_task = Task(
        description=(
            f"Fetch the latest headlines for these topics: {config.NEWS_TOPICS}, "
            f"up to {config.MAX_PER_TOPIC} per topic. Use the news_fetcher tool once, "
            "passing all topics."
        ),
        expected_output="A JSON list of article dicts (title, source, url, published_at, topic).",
        agent=agents["news_fetcher"],
    )

    summarize_task = Task(
        description=(
            "For every fetched article, call summarize_article to produce a short, "
            "clear, factual update. Do this for ALL articles, not just some."
        ),
        expected_output=(
            "A JSON list of {title, source, url, topic, summary}, one entry per article."
        ),
        agent=agents["summarizer"],
        context=[fetch_task],
    )

    publish_task = Task(
        description=(
            "For every summarized article, call post_to_slack with the headline, "
            "summary, and source link."
        ),
        expected_output="A JSON list of {title, posted: true/false} for every article.",
        agent=agents["publisher"],
        context=[summarize_task],
    )

    log_task = Task(
        description=(
            "For every article that was posted to Slack, call log_to_sheet with "
            "topic, headline, summary, and source_urls so the Sheet has a full record."
        ),
        expected_output="Confirmation that every posted article was logged to the Sheet.",
        agent=agents["logger"],
        context=[publish_task, summarize_task],
    )

    return [fetch_task, summarize_task, publish_task, log_task]