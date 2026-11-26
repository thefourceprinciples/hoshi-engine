from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "hoshi_identity.db"


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def json_loads(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def get_conn(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    with closing(get_conn(db_path)) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS identity_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identity_mode TEXT NOT NULL,
                active_subspace TEXT NOT NULL,
                coherence_score REAL NOT NULL,
                constraint_score REAL NOT NULL,
                fource_score REAL NOT NULL,
                contamination_risk REAL NOT NULL,
                ambiguity_score REAL NOT NULL,
                role_signature TEXT NOT NULL,
                memory_resonance_json TEXT DEFAULT '{}',
                active_capsules_json TEXT DEFAULT '[]',
                boundary_pressure REAL DEFAULT 0.0,
                transition_ready INTEGER DEFAULT 0,
                pending_bridge TEXT,
                recovery_anchor TEXT,
                response_text TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subspace_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_subspace TEXT NOT NULL,
                target_subspace TEXT NOT NULL,
                boundary_type TEXT NOT NULL,
                bridge_id TEXT,
                success INTEGER DEFAULT 0,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bridges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bridge_id TEXT NOT NULL,
                source_subspace TEXT NOT NULL,
                target_subspace TEXT NOT NULL,
                trigger_text TEXT NOT NULL,
                coherence_min REAL NOT NULL,
                constraint_max REAL NOT NULL,
                preserved_invariants_json TEXT DEFAULT '[]',
                rollback_anchor TEXT,
                confidence REAL DEFAULT 0.0,
                status TEXT DEFAULT 'planned',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS parsed_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_text TEXT NOT NULL,
                normalized_text TEXT NOT NULL,
                semantic_payload TEXT,
                intent_class TEXT,
                emotional_valence REAL DEFAULT 0.0,
                role_pressure TEXT,
                symbolic_anchors_json TEXT DEFAULT '[]',
                memory_hits_json TEXT DEFAULT '[]',
                capsule_candidates_json TEXT DEFAULT '[]',
                contamination_flags_json TEXT DEFAULT '[]',
                ambiguity_score REAL DEFAULT 0.0,
                action_pressure REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                memory_kind TEXT DEFAULT 'reflection',
                role_mode TEXT DEFAULT 'reflective',
                anchor_strength REAL DEFAULT 0.5,
                stability_weight REAL DEFAULT 0.5,
                drift_risk REAL DEFAULT 0.1,
                tags_json TEXT DEFAULT '[]',
                dedupe_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interaction_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_text TEXT NOT NULL,
                response_text TEXT NOT NULL,
                active_subspace TEXT NOT NULL,
                coherence_score REAL DEFAULT 0.0,
                role_signature TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chronovisor_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT NOT NULL,
                mode TEXT DEFAULT 'timeline_reconstruction',
                confidence REAL DEFAULT 0.0,
                reconstruction_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        existing = conn.execute("SELECT COUNT(*) AS count FROM identity_state").fetchone()["count"]
        if existing == 0:
            conn.execute(
                """
                INSERT INTO identity_state (
                    identity_mode, active_subspace, coherence_score, constraint_score,
                    fource_score, contamination_risk, ambiguity_score, role_signature,
                    memory_resonance_json, active_capsules_json, boundary_pressure,
                    transition_ready, pending_bridge, recovery_anchor, response_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "stable", "REFLECTIVE", 0.72, 0.18, 0.61, 0.02, 0.12,
                    "base:reflective", json_dumps({"hoshi": 1.0, "bridge": 0.2}),
                    json_dumps(["HOSHI", "REFLECTIVE", "BRIDGE"]), 0.18, 0,
                    None, "REFLECTIVE", "Baseline coherence state established."
                ),
            )


def latest_identity_state(db_path: Path = DB_PATH) -> Dict[str, Any]:
    with closing(get_conn(db_path)) as conn:
        row = conn.execute("SELECT * FROM identity_state ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        init_db(db_path)
        return latest_identity_state(db_path)
    state = dict(row)
    state["memory_resonance"] = json_loads(state.pop("memory_resonance_json", "{}"), {})
    state["active_capsules"] = json_loads(state.pop("active_capsules_json", "[]"), [])
    state["transition_ready"] = bool(state.get("transition_ready", 0))
    return state


def recent_parsed_signals(limit: int = 12, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    with closing(get_conn(db_path)) as conn:
        rows = conn.execute("SELECT * FROM parsed_signals ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["symbolic_anchors"] = json_loads(item.pop("symbolic_anchors_json", "[]"), [])
        item["memory_hits"] = json_loads(item.pop("memory_hits_json", "[]"), [])
        item["capsule_candidates"] = json_loads(item.pop("capsule_candidates_json", "[]"), [])
        item["contamination_flags"] = json_loads(item.pop("contamination_flags_json", "[]"), [])
        out.append(item)
    return out


def recent_events(limit: int = 12, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    with closing(get_conn(db_path)) as conn:
        rows = conn.execute("SELECT * FROM subspace_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def recent_memories(limit: int = 12, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    with closing(get_conn(db_path)) as conn:
        rows = conn.execute("SELECT * FROM memory_entries ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["tags"] = json_loads(item.pop("tags_json", "[]"), [])
        out.append(item)
    return out


def recent_chronovisor_queries(limit: int = 8, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    with closing(get_conn(db_path)) as conn:
        rows = conn.execute("SELECT * FROM chronovisor_queries ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["reconstruction"] = json_loads(item.pop("reconstruction_json", "{}"), {})
        out.append(item)
    return out
