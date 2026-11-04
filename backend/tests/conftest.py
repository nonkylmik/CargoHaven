import os
import os
from pathlib import Path

import pytest

TEST_DATABASE_PATH = Path(__file__).resolve().parents[1] / "seashield_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"

import root_env

# The suite never reads a developer's repository-root .env: its settings (AUTH_REQUIRED, SESSION_SECRET,
# DEMO_USER_*) would otherwise change what the tests see. test_root_env.py covers loading with its own files.
root_env.ROOT_ENV_FILE = Path(__file__).resolve().parent / "no-root-env-during-tests"

from db.database import engine


@pytest.fixture(scope="session", autouse=True)
def isolate_backend_db():
    engine.dispose()
    TEST_DATABASE_PATH.unlink(missing_ok=True)
    yield
    engine.dispose()
    TEST_DATABASE_PATH.unlink(missing_ok=True)
