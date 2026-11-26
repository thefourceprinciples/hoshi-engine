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


def test_flask_api_health_and_cors():
    app = create_app()
    client = app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == "*"
    data = resp.get_json()
    assert data["status"] == "ok"
