"""The product is named CargoHaven (formerly SeaShield). Visible names change; compatibility identifiers do not."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, seed_safety_demo_data
from auth import DEMO_EMAIL, SESSION_COOKIE
from db.database import Base
from db.repositories.safety_repository import list_safety_rounds


def test_openapi_title_names_cargohaven():
    with TestClient(app) as client:
        info = client.get("/openapi.json").json()["info"]
    assert info["title"] == "CargoHaven Security API"
    assert "SeaShield" not in str(info) and "Marisentry" not in str(info)


def test_seeded_demo_records_name_cargohaven(tmp_path):
    database_engine = create_engine(f"sqlite:///{tmp_path / 'branding.db'}")
    Base.metadata.create_all(database_engine)
    with sessionmaker(bind=database_engine, expire_on_commit=False)() as session:
        seed_safety_demo_data(session)
        notes = {round_record.notes for round_record in list_safety_rounds(session)}
    database_engine.dispose()
    assert notes == {"Deterministic CargoHaven demonstration record."}


def test_compatibility_identifiers_keep_their_former_names():
    # Renaming these would sign out every session and break the documented demo login and existing setups.
    assert SESSION_COOKIE == "seashield_session"
    assert DEMO_EMAIL == "operator@seashield.local"
