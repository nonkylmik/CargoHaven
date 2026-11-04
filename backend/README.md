# CargoHaven Backend

The CargoHaven backend is a simulation-only FastAPI service (API version `1.9.0`). It runs the simulation engine, correlates simulated security events into incidents, scores vessels, persists state through SQLAlchemy and Alembic, and broadcasts changes over a WebSocket. It never connects to real vessels, cameras, networks, credentials or security infrastructure.

For the product overview and the frontend, see the [root README](../README.md).

- **Database:** SQLite by default (`backend/seashield.db`). PostgreSQL support exists in code but has not been verified against a running server.
- **Python:** 3.12 or newer (provisional minimum, not yet declared in config). CI tests 3.12 and 3.13.
- **Not included:** production deployment, TLS termination and hardening. The Docker setup below is for development only.

---

## Local development

All commands run from the `backend/` directory. The virtual environment lives in `backend/.venv/` (gitignored, and excluded from the Docker image).

```bash
python -m venv .venv
# Windows (PowerShell):  .\.venv\Scripts\Activate.ps1
# Linux/macOS:           source .venv/bin/activate
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

- Uvicorn serves `http://127.0.0.1:8000`. `GET /health` returns `{"status":"ok","database":"connected","mode":"simulation","version":"1.9.0"}`.
- The interactive API reference is at `http://localhost:8000/docs`.
- Run `alembic upgrade head` before the first start so the database is migration-tracked. A database created by starting the backend first is unversioned; see "Existing databases created without migrations" in the [root README](../README.md#existing-databases-created-without-migrations) before stamping anything.
- Startup and Alembic write to the configured database, and startup seeds demo safety rounds. To experiment without touching `backend/seashield.db`, set `DATABASE_URL=sqlite:///<scratch path>.db` first.

### Tests

With the virtual environment active, from `backend/`:

```bash
python -m pytest
```

`pyproject.toml` sets the test path and `-q`. `tests/conftest.py` points `DATABASE_URL` at a throwaway `backend/seashield_test.db`, so the suite never touches `backend/seashield.db`, and stops the suite from reading a root `.env`, so local settings cannot change test results. `tests/test_root_env.py` covers `.env` loading with its own temporary files. CI runs the same suite on Python 3.12 and 3.13, then applies all migrations to a fresh SQLite database.

---

## Docker (development)

An optional alternative to the local workflow. Only the backend runs in Docker; the frontend still runs on the host with `npm run dev` and reaches the API at its default `http://localhost:8000`.

From the repository root:

```bash
docker compose up --build                                    # build the image and start the backend
docker compose down                                          # stop and remove the container (data is kept)
docker compose run --rm --no-deps backend python -m pytest   # run the test suite in the image
```

- **Startup:** the container runs `alembic upgrade head`, then Uvicorn on `0.0.0.0:8000` inside the container. Compose publishes it on `127.0.0.1:8000` only, so it is not reachable from other machines. Code changes need `docker compose up --build`; there is no auto-reload.
- **Image:** `python:3.12-slim`, running as the non-root user `seashield`.
- **Database:** SQLite at `/data/seashield.db` in the named volume `seashield-data`. It survives `docker compose down` and container rebuilds, and is separate from the host's `backend/seashield.db`. `docker compose down -v` deletes the volume and all its data.
- **Secrets:** the image is built from `backend/` only, and `backend/.dockerignore` excludes `.env*`, `*.db` and `.venv`, so no local secrets, databases or environments are copied into it.
- **Port 8000:** stop any host-run backend first; only one of them can use the port.

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | SQLite file `backend/seashield.db`; `compose.yaml` sets `sqlite:////data/seashield.db` | SQLAlchemy database URL, also used by Alembic |
| `AUTH_REQUIRED` | `false` | `true`, `1`, `yes` or `on` requires a session for the API and the WebSocket |
| `SESSION_SECRET` | development placeholder | Signs session cookies. Startup fails when `AUTH_REQUIRED` is on and this is not set |
| `DEMO_USER_EMAIL` | `operator@seashield.local` | Demo user login |
| `DEMO_USER_PASSWORD` | `seashield-demo` | Demo user password |

Where the values come from:

- **Local development:** set any of the five in the shell environment or in a root `.env` file (gitignored). A variable set in the shell takes precedence over the same variable in `.env`. `root_env.py` loads the file, and both `auth.py` and `db/database.py` call `load_root_env()` before reading their settings, so the result does not depend on which module is imported first (`app/main.py` imports `auth` before `db.database`). Settings are read once at startup; restart the backend after changing them.
- **Docker:** `compose.yaml` sets `DATABASE_URL` and passes the other four through from your shell or a root `.env` file, which Docker Compose reads. When unset, the defaults above apply (authentication off).

Any new module that reads settings from the environment at import time must call `load_root_env()` first; relying on another module to have loaded `.env` makes the result depend on import order.

The demo login defaults keep the product's former name for compatibility with existing setups.

---

## Code layout

| Path | Contents |
|---|---|
| `app/main.py` | FastAPI app: HTTP routes, `/ws/security`, startup (create tables, seed demo safety rounds, re-sync the engine) |
| `auth.py` | Optional demo authentication and session cookies |
| `root_env.py` | Loads the repository-root `.env` for host runs (`load_root_env()`) |
| `websocket_manager.py` | In-memory broadcast to connected WebSocket clients |
| `db/` | Engine and models (`database.py`, `models.py`), event helpers, migration checks, repositories in `db/repositories/` |
| `alembic/` | Migrations `0001`–`0006` (`versions/YYYYMMDD_NNNN_*.py`) |
| `models/`, `schemas/` | Pydantic contracts: events, incidents, positions, safety rounds, security status, API schemas |
| `simulation/` | Event library (`event_generator.py`), scenarios (`scenario_manager.py`), engine (`simulation_engine.py`), simulated vessel positions (`vessel_positions.py`) |
| `security_engine/` | Correlation rules, risk scoring, in-memory incident manager |
| `tests/` | pytest suite and migration fixtures |

The global `SimulationEngine` keeps in-memory events, incidents and scores alongside the database and is re-synced from it at startup.

---

## API overview

The full, current reference is the OpenAPI UI at `/docs`. New routes go under `/api/v1`.

| Area | Endpoints |
|---|---|
| Health and authentication | `GET /health`; `GET /api/auth/config` (`{"auth_required": …}`); `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` |
| Vessels and fleet | `GET /api/v1/vessels`, `GET /api/v1/vessels/{vessel_id}`, `GET /api/v1/vessels/positions` (optional `vessel_id`), `GET /api/v1/fleet/security-summary` |
| Cameras | `GET /api/v1/cameras` (optional `vessel_id`) |
| Security events | `GET /api/security-events` (`limit` 1–500, default 50; `offset`; filters `severity`, `event_type`, `status`, `scenario`, `vessel_id`, `start`, `end`); `GET`, `DELETE /api/security-events/{event_id}`; `POST /api/security-events`; `POST /api/security-events/{event_id}/acknowledge`; `GET /api/v1/events` (optional `vessel_id`) |
| Incidents | `GET`, `POST /api/v1/incidents`; `GET`, `PATCH /api/v1/incidents/{incident_id}`; `POST /api/v1/incidents/{incident_id}/notes`; `POST /api/v1/incidents/{incident_id}/reopen` |
| Safety rounds | `GET /api/v1/safety-round-templates`; `GET`, `POST /api/v1/safety-rounds`; `GET /api/v1/safety-rounds/{round_id}`; `POST …/start`, `…/complete`, `…/cancel`; `GET …/checkpoints`; `PATCH …/checkpoints/{checkpoint_id}` |
| Safety findings | `GET`, `POST /api/v1/safety-findings`; `GET`, `PATCH /api/v1/safety-findings/{finding_id}` |
| Simulation | `GET /api/v1/simulation/scenarios`, `GET /api/v1/simulation/status`, `GET /api/v1/simulation/log` (`limit` 1–200, default 40); `POST /api/v1/simulation/start` (`{"scenario": "<key>"}`), `POST /api/v1/simulation/scenario/{scenario_name}/start`, `POST /api/v1/simulation/next`; `POST /api/v1/simulation/pause`, `/resume`, `/stop`, `/reset`; `POST /api/v1/simulation/inject` (`{"vessel_id": "…", "event_type": "…"}`) |
| Real-time | WebSocket `/ws/security` |
| Legacy (unversioned) | `GET /vessels`, `GET /events`, `GET /incidents`, `GET`, `PATCH /incidents/{incident_id}`, `GET /security/{vessel_id}`, `GET /simulation/status`, `POST /simulation/start`, `/stop`, `/pause`, `/resume`, `/reset`, `/tick`, `POST /simulation/scenario/{scenario_name}/start` |

Legacy routes stay available for compatibility. When `AUTH_REQUIRED` is on, every route except `/health`, the `/api/auth/*` routes and the API docs needs a session, and the WebSocket closes with code `4401` without one.

---

## Simulation scenarios

All events are fictional labels. For example, `FAILED_AUTHENTICATION` does not attempt authentication, and `UNKNOWN_DEVICE` does not scan a network.

| Key | Name | Vessel | Steps |
|---|---|---|---|
| `cyber-intrusion` | Cyber Intrusion Simulation | `calypso` | `UNKNOWN_DEVICE`, `FAILED_AUTHENTICATION` ×2, `SUSPICIOUS_TRAFFIC`, `FIREWALL_BLOCK` |
| `physical-breach` | Physical Breach Simulation | `calypso` | `UNAUTHORIZED_ACCESS`, `CAMERA_OFFLINE` |
| `navigation-anomaly` | Navigation Anomaly Simulation | `atlantic-trader` | `GPS_ANOMALY`, `AIS_ANOMALY`, `COMMUNICATION_INSTABILITY` |
| `fire-emergency` | Fire Emergency Simulation | `northern-star` | `SMOKE_DETECTED`, `FIRE_ALARM`, `TEMPERATURE_HIGH` |

Start a scenario with `POST /api/v1/simulation/start` and advance it one step at a time with `POST /api/v1/simulation/next`. Single events injected from the UI are tagged with the scenario `manual-injection`. The correlation rules and score penalties are documented in the [root README](../README.md#security-simulation-and-event-correlation).

`GET /api/v1/simulation/log` lists what the simulation recorded, newest first: events from scenario steps and manual injections (not safety-round reports or events ingested over REST), each with `scenario_label`, `status` and the `incident_ids` it was correlated into. A failed injection records nothing. If only this endpoint fails, the UI keeps refreshing everything else, keeps the last log it received and marks the log as unavailable.

**Reset** resolves open security events and closes incidents that are still open (`NEW`, `INVESTIGATING`, `CONTAINED`) as `RESOLVED`, adding a "Closed by simulation reset" entry to each one's activity timeline. `RESOLVED` and `FALSE POSITIVE` incidents and all investigation notes are left unchanged, and logged events are resolved but kept. These changes and the recalculated scores commit in one transaction; if it fails, nothing changes.

---

## Behaviour reference

### Vessel security status

`status` on every vessel (`/vessels`, `/api/v1/vessels`, `/api/v1/vessels/{vessel_id}`, `/security/{vessel_id}`) and in `security_score_changed` / `vessel_status_changed` messages is derived from the current `score` by `models/security_status.py`:

| `status`   | `score` |
| ---------- | ------- |
| `SECURE`   | 86–100  |
| `ELEVATED` | 72–85   |
| `WARNING`  | 55–71   |
| `CRITICAL` | 0–54    |

This changed in V4: earlier versions returned only `SECURE` (85–100), `WARNING` (60–84) and `CRITICAL` (0–59). The frontend is the only client and is deployed together with the backend; before any third-party client depends on `/api/v1`, a change like this needs explicit versioning or a compatibility plan.

`GET /api/v1/fleet/security-summary` returns `{ "vessel_count", "average_score", "average_status" }`: the fleet's mean score (rounded half up) and the classification of that average under the same bands. It is not the worst vessel's status; the UI shows the fleet status (the most severe vessel status) separately.

### Incident lifecycle

`PATCH /api/v1/incidents/{incident_id}` changes status only along these transitions (`models/incidents.py`); any other status change returns 409 and changes nothing:

| From                         | To                                                         |
| ---------------------------- | ---------------------------------------------------------- |
| `NEW`                        | `INVESTIGATING`, `CONTAINED`, `RESOLVED`, `FALSE POSITIVE` |
| `INVESTIGATING`              | `CONTAINED`, `RESOLVED`, `FALSE POSITIVE`                  |
| `CONTAINED`                  | `INVESTIGATING`, `RESOLVED`, `FALSE POSITIVE`              |
| `RESOLVED`, `FALSE POSITIVE` | closed: only `POST .../reopen`                             |

Closing an incident resolves its linked events. `POST /api/v1/incidents/{incident_id}/reopen` (a required `reason`, up to 500 characters) returns a `RESOLVED` or `FALSE POSITIVE` incident to `INVESTIGATING`, reopens its linked events so their score penalties return, and records one activity entry with the reason; it adds no evidence links and returns 409 for an incident that is not closed. Status changes and reopening commit together with the recalculated scores. Activity entries record the signed-in user; a name in the request is used only when authentication is disabled. Every incident payload includes `allowed_transitions` and `can_reopen`, which the UI uses to offer only valid actions.

### Vessel last communication

`last_communication` is the time of the most recent security event recorded for the vessel, from any source (simulation steps and injections, `POST /api/security-events`, safety-round reports). It uses the event's own timestamp, clamped to the server's current time, and only moves forward. Score recalculation, startup sync, reset and event deletion never change it, for any vessel. A vessel row created for the first time starts at its creation time. The UI measures its age against the real clock and shows a missing or invalid value as unknown.

### Security events over REST

`POST /api/security-events` returns 404 for an unknown `vessel_id` and 409 for an existing `event_id`. `DELETE /api/security-events/{event_id}` returns 404 for an unknown event and 409 when the event is linked to an incident: incident evidence is never removed, so the event, its incident links and its acknowledgement stay intact. Deleting an unlinked event also deletes its acknowledgement. Both routes commit the event change and the recalculated vessel scores in one transaction, then broadcast `security_event_created` or `security_event_deleted`; if the transaction fails, nothing is written and no score notification is sent. A duplicate `event_id` that a concurrent request commits first also returns 409.

Deletion checks incident links only after it holds the SQLite write lock, and incident creation verifies its linked events under the same lock, so a linked event cannot be deleted even when both requests run concurrently. This relies on SQLite's single writer; PostgreSQL would need a database constraint, which is not yet in place. Deletion is unrestricted for any signed-in user in the local pilot; soft deletion or administrative permissions are to be decided before external users get access.

### Authentication

`POST /api/auth/login` sets an HTTP-only, `SameSite=Lax` session cookie (`seashield_session`, kept under its former name for compatibility) that is valid for 8 hours; `POST /api/auth/logout` clears it and `GET /api/auth/me` returns the signed-in user. The cookie is not marked `Secure`, because the development backend serves plain HTTP. With authentication off (the default), all routes are open.
