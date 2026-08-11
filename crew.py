"""
Builds and runs the single Crew for the pipeline: fetch -> summarize -> post
to Slack -> log to Sheet.
"""
from crewai import Crew, Process

from agents import build_agents
from tasks import build_tasks


def run_news_crew(topics: list | None = None, max_per_topic: int | None = None) -> str:
    """
    topics=None runs the default configured topics (used by the 6-hour /
    daily crons). A caller can override with a specific list -- that's how
    the dashboard's "type any topic, get news" trigger works.
    """
    agents = build_agents()
    tasks = build_tasks(agents, topics=topics, max_per_topic=max_per_topic)
    crew = Crew(
        agents=[agents["news_fetcher"], agents["summarizer"], agents["publisher"], agents["logger"]],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
    return crew.kickoff()