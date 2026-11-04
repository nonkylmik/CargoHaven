"""Loads the repository-root .env file for host runs.

Every module that reads settings from the environment at import time calls load_root_env() first, so the
result no longer depends on import order. Variables already set in the process environment take precedence
over the file (python-dotenv's default), and repeated calls change nothing. Docker images contain no .env
file (backend/.dockerignore), so there this is a no-op and Compose's environment applies unchanged.
"""
from pathlib import Path

from dotenv import load_dotenv

ROOT_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def load_root_env() -> None:
    load_dotenv(ROOT_ENV_FILE)
