"""
Builds and runs the single Crew for the pipeline: fetch -> summarize -> post
to Slack -> log to Sheet.
"""
from crewai import Crew, Process

from agents import build_agents
from tasks import build_tasks


def run_news_crew() -> str:
    agents = build_agents()
    tasks = build_tasks(agents)
    crew = Crew(
        agents=[agents["news_fetcher"], agents["summarizer"], agents["publisher"], agents["logger"]],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
    return crew.kickoff()