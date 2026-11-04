"""Host runs read settings from the repository-root .env, whatever the import order.

app.main imports auth before db.database. auth reads SESSION_SECRET and DEMO_USER_* at import, and only
db.database used to load .env, so those values were ignored on the host. Each case runs in a fresh
interpreter (the bug only shows on first import) with its own temporary .env file and SQLite database, and
without the variables below in its environment, so the real .env, the user's environment and
backend/seashield.db are never read or written.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
SETTINGS = ("DATABASE_URL", "AUTH_REQUIRED", "SESSION_SECRET", "DEMO_USER_EMAIL", "DEMO_USER_PASSWORD")

HOST_RUN = textwrap.dedent(
    """
    import json, sys
    from pathlib import Path
    sys.path.insert(0, sys.argv[1])
    import root_env
    root_env.ROOT_ENV_FILE = Path(sys.argv[2])

    import app.main  # the real import order: auth before db.database
    import auth
    from db import database
    from fastapi.testclient import TestClient

    result = {
        "session_secret": auth.SESSION_SECRET,
        "demo_email": auth.DEMO_USER.email,
        "demo_password": auth.DEMO_PASSWORD,
        "auth_required": auth.auth_required(),
        "database_url": database.DATABASE_URL,
        "login_ok": auth.authenticate(sys.argv[3], sys.argv[4]) is not None,
        "startup_error": None,
    }
    try:
        with TestClient(app.main.app) as client:
            result["health"] = client.get("/health").status_code
    except RuntimeError as error:
        result["startup_error"] = str(error)
    print(json.dumps(result))
    """
)


def host_run(tmp_path: Path, env_file: str | None, environ: dict[str, str] | None = None, login=("", "")) -> dict:
    """Imports the backend as a host run would, with `env_file` as the root .env (None: no file)."""
    env_path = tmp_path / "root.env"
    if env_file is not None:
        env_path.write_text(textwrap.dedent(env_file), encoding="utf-8")
    child_env = {key: value for key, value in os.environ.items() if key not in SETTINGS}
    if environ is not None:
        child_env.update(environ)
    completed = subprocess.run(
        [sys.executable, "-c", HOST_RUN, str(BACKEND_DIR), str(env_path), *login],
        cwd=tmp_path,
        env=child_env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout.strip().splitlines()[-1])


def sqlite_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'host.db').as_posix()}"


def test_session_secret_from_root_env_lets_required_auth_start(tmp_path):
    result = host_run(
        tmp_path,
        """
        AUTH_REQUIRED=true
        SESSION_SECRET=secret-from-root-env
        """,
        {"DATABASE_URL": sqlite_url(tmp_path)},
    )
    assert result["session_secret"] == "secret-from-root-env"
    assert result["auth_required"] is True
    assert result["startup_error"] is None
    assert result["health"] == 200


def test_demo_user_from_root_env(tmp_path):
    result = host_run(
        tmp_path,
        """
        DEMO_USER_EMAIL=operator@example.test
        DEMO_USER_PASSWORD=password-from-root-env
        """,
        {"DATABASE_URL": sqlite_url(tmp_path)},
        login=("operator@example.test", "password-from-root-env"),
    )
    assert result["demo_email"] == "operator@example.test"
    assert result["demo_password"] == "password-from-root-env"
    assert result["login_ok"] is True


def test_required_auth_without_session_secret_still_refuses_to_start(tmp_path):
    result = host_run(tmp_path, "AUTH_REQUIRED=true\n", {"DATABASE_URL": sqlite_url(tmp_path)})
    assert result["auth_required"] is True
    assert result["startup_error"] == (
        "AUTH_REQUIRED is enabled but SESSION_SECRET is not set. Set SESSION_SECRET to a long random value."
    )
    assert "health" not in result


def test_database_url_and_auth_required_from_root_env(tmp_path):
    url = sqlite_url(tmp_path)
    result = host_run(tmp_path, f"DATABASE_URL={url}\nAUTH_REQUIRED=false\n")
    assert result["database_url"] == url
    assert result["auth_required"] is False
    assert result["health"] == 200
    assert (tmp_path / "host.db").exists()


def test_process_environment_takes_precedence_over_root_env(tmp_path):
    result = host_run(
        tmp_path,
        """
        SESSION_SECRET=secret-from-root-env
        DEMO_USER_EMAIL=file@example.test
        AUTH_REQUIRED=true
        """,
        {"DATABASE_URL": sqlite_url(tmp_path), "SESSION_SECRET": "secret-from-shell", "AUTH_REQUIRED": "false"},
    )
    assert result["session_secret"] == "secret-from-shell"
    assert result["demo_email"] == "file@example.test"
    assert result["auth_required"] is False


def test_without_root_env_the_defaults_apply(tmp_path):
    # As in the Docker image, which contains no .env file.
    result = host_run(tmp_path, None, {"DATABASE_URL": sqlite_url(tmp_path)})
    assert result["session_secret"] == "change-me-in-development"
    assert result["demo_email"] == "operator@seashield.local"
    assert result["auth_required"] is False
    assert result["startup_error"] is None
