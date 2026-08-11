"""
Task definitions for the single linear pipeline: fetch -> summarize -> post to
Slack -> log to Sheet. All four run in one Crew, one process.
"""
from crewai import Task

from config import config


def build_tasks(agents: dict, topics: list | None = None, max_per_topic: int | None = None):
    topics = topics if topics else config.NEWS_TOPICS
    max_per_topic = max_per_topic if max_per_topic else config.MAX_PER_TOPIC

    # Rendered as plain comma-separated text, not a Python list repr --
    # "spacex" reads unambiguously as one topic; ['spacex'] can get
    # misparsed or blended with the agent's own "configured topics" framing
    # by smaller/faster models. Repeating the instruction and explicitly
    # forbidding substitution closes that gap.
    topics_list_text = ", ".join(topics)

    fetch_task = Task(
        description=(
            f"Fetch headlines for EXACTLY these {len(topics)} topic(s), and no others: "
            f"{topics_list_text}.\n\n"
            f"Call the news_fetcher tool exactly once, passing topics=[{topics_list_text}] "
            f"(as a list of strings) and max_per_topic={max_per_topic}.\n\n"
            "Do NOT substitute, add, or fall back to any other topics -- including any "
            "topics mentioned in your own role description or past runs. Use only the "
            "topic list given in this task."
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