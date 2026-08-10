"""Entrypoint: run the full news pipeline once (fetch -> summarize -> post -> log)."""
import sys

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from crew import run_news_crew

if __name__ == "__main__":
    result = run_news_crew()
    print(result)