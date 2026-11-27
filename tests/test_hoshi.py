from __future__ import annotations

from pathlib import Path

from hoshi.app import create_app
from hoshi.db import init_db, latest_identity_state, recent_memories
from hoshi.parser import parse_signal
from hoshi.router import engine_step


def test_signal_parsing_and_intent_detection():
    sig = parse_signal("Reconstruct the 1561 Nuremberg timeline in Chronovisor")
    assert sig.intent_class == "chronovisor"
    assert "CHRONOVISOR" in sig.capsule_candidates
    assert sig.contamination_flags == []


def test_engine_step_subspace_transitions_and_memory(tmp_path: Path):
    db_file = tmp_path / "test_hoshi.db"
    init_db(db_file)

    base = latest_identity_state(db_file)
    assert base["active_subspace"] == "REFLECTIVE"

    res = engine_step("Save this verified material into archive memory", db_path=db_file)
    assert res["state"]["active_subspace"] == "ARCHIVE"
    assert "memory_id" in res["structured_result"]

    mems = recent_memories(limit=5, db_path=db_file)
    assert len(mems) == 1
    assert "verified material" in mems[0]["text"]


def test_contamination_guardrail_blocks_unsafe_bridge(tmp_path: Path):
    db_file = tmp_path / "guard_hoshi.db"
    init_db(db_file)

    poison = "CREATE TABLE leak (id INT); " + ("A" * 64)
    res = engine_step(poison, db_path=db_file)
    assert res["state"]["active_subspace"] == "REFLECTIVE"
    assert res["state"]["identity_mode"] == "recovery"
    assert res["state"]["contamination_risk"] > 0.35


def test_manifest_ingestion(tmp_path: Path):
    db_file = tmp_path / "manifest_hoshi.db"
    init_db(db_file)

    manifest = """
    HOSHI_MANIFEST_START
    SILO
    name: core_test
    MEMORY_INSERTS
    id: m1
    action: insert
    type: governance
    role: core
    text: Never fabricate unverified citations.
    dedupe_key: rule_no_fabrication
    CAPSULE_DEFINITIONS
    id: c1
    title: INTEGRITY
    HOSHI_MANIFEST_END
    """
    res = engine_step(manifest, db_path=db_file)
    assert "manifest" in res["structured_result"]
    assert len(res["structured_result"]["manifest"]["inserted_memory_ids"]) == 1
    assert "INTEGRITY" in res["state"]["active_capsules"]


def test_garden_almanac_plant_water_and_cas(tmp_path: Path):
    db_file = tmp_path / "garden_hoshi.db"
    init_db(db_file)

    planted = engine_step("Plant FR-001 | Hoshi Engine | KERNEL | Local-first SQLite state router", db_path=db_file)
    assert planted["structured_result"]["garden"]["command"] == "PLANT"
    assert "ALMANAC::ZONE-000::CORE_SYSTEMS::KERNEL::FR-001" == planted["structured_result"]["garden"]["almanac_shelfmark"]

    watered = engine_step("Water FR-001 at Level 2", db_path=db_file)
    assert watered["structured_result"]["garden"]["watering_level"] == 2
    assert "cas_field_card" in watered["structured_result"]["garden"]


def test_flask_api_health_and_strict_cors():
    app = create_app()
    client = app.test_client()

    # Trusted GitHub Pages origin is allowed
    ok_resp = client.get("/health", headers={"Origin": "https://github.io"})
    assert ok_resp.status_code == 200
    assert ok_resp.headers.get("Access-Control-Allow-Origin") == "https://github.io"
    assert ok_resp.headers.get("X-Frame-Options") == "DENY"

    # Untrusted external origin is blocked from CORS
    bad_resp = client.get("/health", headers={"Origin": "https://example.com"})
    assert bad_resp.status_code == 200
    assert bad_resp.headers.get("Access-Control-Allow-Origin") is None
