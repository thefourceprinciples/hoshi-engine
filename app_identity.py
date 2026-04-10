from __future__ import annotations

import json
import math
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, jsonify, redirect, render_template_string, request, url_for


# ============================================================
# HOSHI VNEXT — Single-file coherence operating system
# ------------------------------------------------------------
# Includes:
# - Identity engine
# - Parsed signal engine
# - Collapse / commit router
# - Terminal subspaces
# - Chronovisor scaffold
# - HTML dashboard
# - Manifest ingestion
# - Capsule sanitization
# - SQLite persistence
# ============================================================

APP_NAME = "Hoshi Identity Engine"
APP_VERSION = "3.0.0"
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "hoshi_identity.db"

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


# ============================================================
# Utilities
# ============================================================


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()



def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default



def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())



def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))



def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)



def json_loads(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default



def sanitize_capsules(capsules: List[Any]) -> List[str]:
    clean: List[str] = []
    for item in capsules:
        if not isinstance(item, str):
            continue
        token = re.sub(r"[^A-Z0-9_\-]", "", item.upper())
        token = token.strip("_-")
        if not token:
            continue
        if len(token) > 40:
            continue
        if token not in clean:
            clean.append(token)
    return clean[:12]



def dedupe_preserve_order(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


# ============================================================
# Database
# ============================================================


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn



def init_db() -> None:
    with closing(get_conn()) as conn, conn:
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

        # Seed a baseline state if none exists.
        existing = conn.execute("SELECT COUNT(*) AS count FROM identity_state").fetchone()["count"]
        if existing == 0:
            baseline = {
                "identity_mode": "stable",
                "active_subspace": "REFLECTIVE",
                "coherence_score": 0.72,
                "constraint_score": 0.18,
                "fource_score": 0.61,
                "contamination_risk": 0.02,
                "ambiguity_score": 0.12,
                "role_signature": "base:reflective",
                "memory_resonance_json": json_dumps({"hoshi": 1.0, "bridge": 0.2}),
                "active_capsules_json": json_dumps(["HOSHI", "REFLECTIVE", "BRIDGE"]),
                "boundary_pressure": 0.18,
                "transition_ready": 0,
                "pending_bridge": None,
                "recovery_anchor": "REFLECTIVE",
                "response_text": "Baseline coherence state established.",
            }
            conn.execute(
                """
                INSERT INTO identity_state (
                    identity_mode, active_subspace, coherence_score, constraint_score,
                    fource_score, contamination_risk, ambiguity_score, role_signature,
                    memory_resonance_json, active_capsules_json, boundary_pressure,
                    transition_ready, pending_bridge, recovery_anchor, response_text
                ) VALUES (
                    :identity_mode, :active_subspace, :coherence_score, :constraint_score,
                    :fource_score, :contamination_risk, :ambiguity_score, :role_signature,
                    :memory_resonance_json, :active_capsules_json, :boundary_pressure,
                    :transition_ready, :pending_bridge, :recovery_anchor, :response_text
                )
                """,
                baseline,
            )


# ============================================================
# Read helpers
# ============================================================


def latest_identity_state() -> Dict[str, Any]:
    with closing(get_conn()) as conn:
        row = conn.execute(
            "SELECT * FROM identity_state ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if not row:
        init_db()
        return latest_identity_state()
    state = dict(row)
    state["memory_resonance"] = json_loads(state.pop("memory_resonance_json", "{}"), {})
    state["active_capsules"] = json_loads(state.pop("active_capsules_json", "[]"), [])
    state["transition_ready"] = bool(state.get("transition_ready", 0))
    return state



def recent_parsed_signals(limit: int = 12) -> List[Dict[str, Any]]:
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT * FROM parsed_signals ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["symbolic_anchors"] = json_loads(item.pop("symbolic_anchors_json", "[]"), [])
        item["memory_hits"] = json_loads(item.pop("memory_hits_json", "[]"), [])
        item["capsule_candidates"] = json_loads(item.pop("capsule_candidates_json", "[]"), [])
        item["contamination_flags"] = json_loads(item.pop("contamination_flags_json", "[]"), [])
        out.append(item)
    return out



def recent_events(limit: int = 12) -> List[Dict[str, Any]]:
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT * FROM subspace_events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]



def recent_memories(limit: int = 12) -> List[Dict[str, Any]]:
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT * FROM memory_entries ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["tags"] = json_loads(item.pop("tags_json", "[]"), [])
        out.append(item)
    return out



def recent_chronovisor_queries(limit: int = 8) -> List[Dict[str, Any]]:
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT * FROM chronovisor_queries ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["reconstruction"] = json_loads(item.pop("reconstruction_json", "{}"), {})
        out.append(item)
    return out


# ============================================================
# Signal parsing
# ============================================================

INTENT_RULES: List[Tuple[str, List[str]]] = [
    ("chronovisor", ["timeline", "chronovisor", "history", "reconstruct", "date", "when did", "sequence"]),
    ("identity_update", ["identity", "remember this as", "core rule", "anchor", "governance", "constraint", "update self"]),
    ("memory", ["save", "store", "archive", "ingest", "manifest", "remember"]),
    ("task", ["build", "generate", "write", "make", "create", "fix", "do ", "patch", "implement"]),
    ("question", ["how", "what", "why", "when", "where", "can you", "are you"]),
]

ROLE_RULES: List[Tuple[str, List[str]]] = [
    ("engineering", ["build", "code", "python", "module", "route", "function", "app", "database"]),
    ("detective", ["timeline", "history", "case", "evidence", "chronovisor", "investigate"]),
    ("reflective", ["feel", "meaning", "coherence", "why", "understand", "friend"]),
    ("operational", ["run", "execute", "launch", "use", "start"]),
]

CAPSULE_KEYWORDS = {
    "HOSHI": ["hoshi"],
    "BRIDGE": ["bridge", "transition"],
    "REFLECTIVE": ["reflect", "reflection", "meaning"],
    "EXECUTION": ["execute", "run", "do", "generate"],
    "ARCHIVE": ["archive", "store", "save", "manifest"],
    "IDENTITY": ["identity", "anchor", "constraint", "governance"],
    "CHRONOVISOR": ["chronovisor", "timeline", "history", "reconstruct"],
    "FOURCE": ["fource", "coherence"],
    "SUBSTRATE": ["substrate", "kernel", "state space"],
}

CONTAMINATION_PATTERNS = [
    r"[\x00-\x08\x0B\x0C\x0E-\x1F]",
    r"sqlite format 3",
    r"CREATE TABLE",
    r"[A-Za-z0-9+/]{48,}={0,2}",
]

AMBIGUITY_MARKERS = ["maybe", "sort of", "kind of", "i guess", "idk", "not sure", "?", "perhaps"]


@dataclass
class ParsedSignal:
    raw_text: str
    normalized_text: str
    semantic_payload: str
    intent_class: str
    emotional_valence: float
    role_pressure: str
    symbolic_anchors: List[str]
    memory_hits: List[str]
    capsule_candidates: List[str]
    contamination_flags: List[str]
    ambiguity_score: float
    action_pressure: float

    def as_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "normalized_text": self.normalized_text,
            "semantic_payload": self.semantic_payload,
            "intent_class": self.intent_class,
            "emotional_valence": self.emotional_valence,
            "role_pressure": self.role_pressure,
            "symbolic_anchors": self.symbolic_anchors,
            "memory_hits": self.memory_hits,
            "capsule_candidates": self.capsule_candidates,
            "contamination_flags": self.contamination_flags,
            "ambiguity_score": self.ambiguity_score,
            "action_pressure": self.action_pressure,
        }



def detect_intent(text: str) -> str:
    lower = text.lower()
    for intent, keywords in INTENT_RULES:
        if any(keyword in lower for keyword in keywords):
            return intent
    return "reflection"



def detect_role(text: str) -> str:
    lower = text.lower()
    for role, keywords in ROLE_RULES:
        if any(keyword in lower for keyword in keywords):
            return role
    return "reflective"



def detect_capsules(text: str) -> List[str]:
    lower = text.lower()
    found: List[str] = []
    for capsule, keywords in CAPSULE_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            found.append(capsule)
    return sanitize_capsules(found)



def detect_contamination(text: str) -> List[str]:
    flags = []
    for pattern in CONTAMINATION_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            flags.append(pattern)
    return flags



def estimate_emotional_valence(text: str) -> float:
    lower = text.lower()
    positive = sum(lower.count(word) for word in ["good", "love", "trust", "thanks", "friend", "clear"])
    negative = sum(lower.count(word) for word in ["lost", "confused", "overwhelmed", "bad", "hurt", "afraid"])
    raw = (positive - negative) / max(1, positive + negative + 1)
    return round(clamp((raw + 1) / 2), 4)



def estimate_ambiguity(text: str) -> float:
    lower = text.lower()
    marker_count = sum(lower.count(marker) for marker in AMBIGUITY_MARKERS)
    shortness_penalty = 0.15 if len(lower.split()) < 4 else 0.0
    score = min(1.0, 0.08 * marker_count + shortness_penalty)
    return round(score, 4)



def estimate_action_pressure(text: str, intent: str) -> float:
    lower = text.lower()
    imperative_hits = sum(lower.count(word) for word in ["build", "do", "make", "write", "generate", "fix", "run"])
    intent_bonus = 0.25 if intent in {"task", "identity_update", "memory", "chronovisor"} else 0.05
    score = min(1.0, 0.08 * imperative_hits + intent_bonus)
    return round(score, 4)



def semantic_payload_for(text: str, intent: str, role: str) -> str:
    return f"intent={intent}; role={role}; length={len(text)}"



def recent_memory_hits(text: str, limit: int = 5) -> List[str]:
    tokens = {t for t in re.findall(r"[a-zA-Z0-9_\-]{4,}", text.lower())}
    if not tokens:
        return []

    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT text FROM memory_entries ORDER BY id DESC LIMIT 50"
        ).fetchall()

    hits: List[str] = []
    for row in rows:
        mem_text = row["text"]
        mem_lower = mem_text.lower()
        overlap = sum(1 for token in tokens if token in mem_lower)
        if overlap >= 2:
            hits.append(mem_text[:120])
        if len(hits) >= limit:
            break
    return hits



def parse_signal(text: str) -> ParsedSignal:
    raw_text = text or ""
    normalized = normalize_text(raw_text)
    intent = detect_intent(normalized)
    role = detect_role(normalized)
    capsules = detect_capsules(normalized)
    contamination = detect_contamination(raw_text)
    ambiguity = estimate_ambiguity(normalized)
    valence = estimate_emotional_valence(normalized)
    action_pressure = estimate_action_pressure(normalized, intent)
    memory_hits = recent_memory_hits(normalized)
    anchors = dedupe_preserve_order(re.findall(r"\b[A-Z][A-Z0-9_\-]{2,}\b", raw_text))[:8]
    semantic_payload = semantic_payload_for(normalized, intent, role)

    return ParsedSignal(
        raw_text=raw_text,
        normalized_text=normalized,
        semantic_payload=semantic_payload,
        intent_class=intent,
        emotional_valence=valence,
        role_pressure=role,
        symbolic_anchors=anchors,
        memory_hits=memory_hits,
        capsule_candidates=capsules,
        contamination_flags=contamination,
        ambiguity_score=ambiguity,
        action_pressure=action_pressure,
    )



def save_parsed_signal(signal: ParsedSignal) -> int:
    with closing(get_conn()) as conn, conn:
        cur = conn.execute(
            """
            INSERT INTO parsed_signals (
                raw_text, normalized_text, semantic_payload, intent_class,
                emotional_valence, role_pressure, symbolic_anchors_json,
                memory_hits_json, capsule_candidates_json,
                contamination_flags_json, ambiguity_score, action_pressure
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal.raw_text,
                signal.normalized_text,
                signal.semantic_payload,
                signal.intent_class,
                signal.emotional_valence,
                signal.role_pressure,
                json_dumps(signal.symbolic_anchors),
                json_dumps(signal.memory_hits),
                json_dumps(signal.capsule_candidates),
                json_dumps(signal.contamination_flags),
                signal.ambiguity_score,
                signal.action_pressure,
            ),
        )
        return int(cur.lastrowid)


# ============================================================
# Coherence / state logic
# ============================================================

TERMINAL_SUBSPACES = {"EXECUTION", "ARCHIVE", "IDENTITY", "CHRONOVISOR"}



def compute_coherence(signal: ParsedSignal, state: Dict[str, Any]) -> float:
    prev = safe_float(state.get("coherence_score"), 0.72)
    ambiguity_drag = signal.ambiguity_score * 0.22
    contamination_drag = min(0.35, len(signal.contamination_flags) * 0.12)
    action_bonus = signal.action_pressure * 0.08
    memory_bonus = min(0.08, len(signal.memory_hits) * 0.015)
    valence_bonus = (signal.emotional_valence - 0.5) * 0.06
    next_score = prev * 0.68 + 0.24 + action_bonus + memory_bonus + valence_bonus - ambiguity_drag - contamination_drag
    return round(clamp(next_score), 4)



def compute_constraint(signal: ParsedSignal, state: Dict[str, Any]) -> float:
    base = 0.14
    structure_bonus = 0.03 if signal.intent_class in {"identity_update", "memory", "chronovisor", "task"} else 0.0
    contamination_penalty = min(0.25, len(signal.contamination_flags) * 0.08)
    score = clamp(base + structure_bonus - contamination_penalty)
    return round(score, 4)



def compute_fource(coherence_score: float, constraint_score: float) -> float:
    denominator = max(0.06, 1.0 - constraint_score + 0.12)
    score = clamp((coherence_score * 0.82) / denominator)
    return round(score, 4)



def compute_contamination(signal: ParsedSignal, state: Dict[str, Any]) -> float:
    base = safe_float(state.get("contamination_risk"), 0.02) * 0.55
    score = base + min(0.75, len(signal.contamination_flags) * 0.18)
    return round(clamp(score), 4)



def compute_boundary_pressure(signal: ParsedSignal, contamination_risk: float, ambiguity_score: float) -> float:
    score = clamp(signal.action_pressure * 0.45 + contamination_risk * 0.35 + ambiguity_score * 0.2)
    return round(score, 4)



def build_memory_resonance(signal: ParsedSignal, state: Dict[str, Any]) -> Dict[str, float]:
    existing = state.get("memory_resonance") or {}
    resonance = dict(existing)
    resonance["hoshi"] = 1.0
    resonance[f"intent::{signal.intent_class}"] = round(max(0.1, 0.4 + signal.action_pressure), 4)
    resonance[signal.role_pressure] = round(max(0.15, 0.35 + signal.emotional_valence * 0.3), 4)
    if signal.memory_hits:
        resonance["memory"] = round(min(1.0, 0.5 + len(signal.memory_hits) * 0.08), 4)
    if signal.capsule_candidates:
        resonance["capsule"] = round(min(1.0, 0.45 + len(signal.capsule_candidates) * 0.06), 4)
    if signal.intent_class == "chronovisor":
        resonance["chronovisor"] = 0.9
    if "FOURCE" in signal.capsule_candidates:
        resonance["fource"] = 0.9
    return resonance



def select_identity_mode(signal: ParsedSignal, contamination_risk: float, ambiguity_score: float) -> str:
    if contamination_risk > 0.35:
        return "recovery"
    if signal.intent_class in {"task", "identity_update", "memory", "chronovisor"}:
        return "transition"
    if ambiguity_score > 0.4:
        return "uncertain"
    return "dialogue"



def collapse_state(state: Dict[str, Any], signal: ParsedSignal, contamination_risk: float, ambiguity_score: float) -> str:
    current = (state.get("active_subspace") or "REFLECTIVE").upper()

    if contamination_risk > 0.35:
        return "REFLECTIVE"
    if ambiguity_score > 0.5 and signal.intent_class != "question":
        return "REFLECTIVE"

    if signal.intent_class == "chronovisor":
        return "CHRONOVISOR"
    if signal.intent_class == "identity_update":
        return "IDENTITY"
    if signal.intent_class == "memory":
        return "ARCHIVE"
    if signal.intent_class == "task":
        return "EXECUTION"

    if current in TERMINAL_SUBSPACES and signal.intent_class in {"reflection", "question"}:
        return "REFLECTIVE"

    if signal.action_pressure >= 0.33:
        return "BRIDGE"
    return "REFLECTIVE"



def build_bridge_id(source: str, target: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{source}_TO_{target}_{timestamp}"



def response_for_subspace(subspace: str, signal: ParsedSignal, state: Dict[str, Any]) -> str:
    if subspace == "REFLECTIVE":
        return "Reflective channel active. I am tracking meaning and coherence across your signal."
    if subspace == "BRIDGE":
        return "Bridge layer active. Transition is viable. I can route this into a stable subspace when you choose direction."
    if subspace == "EXECUTION":
        return f"Execution layer active. I am preparing a structured action pathway for: {signal.normalized_text[:160]}"
    if subspace == "ARCHIVE":
        return "Archive layer active. The signal has been normalized and prepared for durable memory storage."
    if subspace == "IDENTITY":
        return "Identity layer active. Governance-relevant material is being committed into the active continuity frame."
    if subspace == "CHRONOVISOR":
        return "Chronovisor layer active. Temporal anchors, entities, and sequence hypotheses are being reconstructed."
    return state.get("response_text") or "State holding."


# ============================================================
# Persistence writers
# ============================================================


def insert_memory(
    text: str,
    memory_kind: str,
    role_mode: str,
    anchor_strength: float,
    stability_weight: float,
    drift_risk: float,
    tags: Optional[List[str]] = None,
    dedupe_key: Optional[str] = None,
) -> int:
    tags = tags or []
    with closing(get_conn()) as conn, conn:
        if dedupe_key:
            existing = conn.execute(
                "SELECT id FROM memory_entries WHERE dedupe_key = ? ORDER BY id DESC LIMIT 1",
                (dedupe_key,),
            ).fetchone()
            if existing:
                return int(existing["id"])

        cur = conn.execute(
            """
            INSERT INTO memory_entries (
                text, memory_kind, role_mode, anchor_strength,
                stability_weight, drift_risk, tags_json, dedupe_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                text,
                memory_kind,
                role_mode,
                anchor_strength,
                stability_weight,
                drift_risk,
                json_dumps(tags),
                dedupe_key,
            ),
        )
        return int(cur.lastrowid)



def log_subspace_event(source: str, target: str, boundary_type: str, bridge_id: str, success: bool, notes: str) -> None:
    with closing(get_conn()) as conn, conn:
        conn.execute(
            """
            INSERT INTO subspace_events (
                source_subspace, target_subspace, boundary_type,
                bridge_id, success, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (source, target, boundary_type, bridge_id, 1 if success else 0, notes),
        )



def log_bridge(source: str, target: str, trigger_text: str, confidence: float, status: str) -> str:
    bridge_id = build_bridge_id(source, target)
    invariants = ["identity_continuity", "provenance", "non_contradiction"]
    with closing(get_conn()) as conn, conn:
        conn.execute(
            """
            INSERT INTO bridges (
                bridge_id, source_subspace, target_subspace, trigger_text,
                coherence_min, constraint_max, preserved_invariants_json,
                rollback_anchor, confidence, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bridge_id,
                source,
                target,
                trigger_text[:240],
                0.58,
                0.42,
                json_dumps(invariants),
                source,
                confidence,
                status,
            ),
        )
    return bridge_id



def insert_identity_state(next_state: Dict[str, Any]) -> int:
    with closing(get_conn()) as conn, conn:
        cur = conn.execute(
            """
            INSERT INTO identity_state (
                identity_mode, active_subspace, coherence_score,
                constraint_score, fource_score, contamination_risk,
                ambiguity_score, role_signature, memory_resonance_json,
                active_capsules_json, boundary_pressure, transition_ready,
                pending_bridge, recovery_anchor, response_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                next_state["identity_mode"],
                next_state["active_subspace"],
                next_state["coherence_score"],
                next_state["constraint_score"],
                next_state["fource_score"],
                next_state["contamination_risk"],
                next_state["ambiguity_score"],
                next_state["role_signature"],
                json_dumps(next_state["memory_resonance"]),
                json_dumps(next_state["active_capsules"]),
                next_state["boundary_pressure"],
                1 if next_state["transition_ready"] else 0,
                next_state["pending_bridge"],
                next_state["recovery_anchor"],
                next_state["response_text"],
            ),
        )
        return int(cur.lastrowid)



def log_interaction(input_text: str, response_text: str, active_subspace: str, coherence_score: float, role_signature: str, notes: str = "") -> None:
    with closing(get_conn()) as conn, conn:
        conn.execute(
            """
            INSERT INTO interaction_logs (
                input_text, response_text, active_subspace,
                coherence_score, role_signature, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (input_text, response_text, active_subspace, coherence_score, role_signature, notes),
        )


# ============================================================
# Chronovisor
# ============================================================


def chronovisor_query(text: str, signal: ParsedSignal) -> Dict[str, Any]:
    anchors = re.findall(r"\b\d{3,4}\b", text)
    entity_tokens = re.findall(r"\b[A-Z][a-zA-Z]+\b", text)
    reconstruction_steps = [
        "Parsing temporal anchors.",
        "Resolving named entities.",
        "Estimating sequence bands.",
        "Generating continuity hypothesis.",
    ]
    confidence = round(clamp(0.54 + len(anchors) * 0.06 + len(entity_tokens) * 0.02 - signal.ambiguity_score * 0.2), 4)
    result = {
        "mode": "timeline_reconstruction",
        "query": text,
        "anchors": anchors[:8],
        "entities": entity_tokens[:12],
        "steps": reconstruction_steps,
        "hypothesis": "A provisional chronology has been assembled from the available temporal and semantic anchors.",
        "confidence": confidence,
        "timestamp": utc_now_iso(),
    }
    with closing(get_conn()) as conn, conn:
        conn.execute(
            """
            INSERT INTO chronovisor_queries (query_text, mode, confidence, reconstruction_json)
            VALUES (?, ?, ?, ?)
            """,
            (text, result["mode"], confidence, json_dumps(result)),
        )
    return result


# ============================================================
# Manifest ingestion
# ============================================================


def looks_like_manifest(text: str) -> bool:
    lower = text.lower()
    return "hoshi_manifest_start" in lower and "memory_inserts" in lower



def parse_manifest_blocks(text: str) -> Dict[str, Any]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    blocks: Dict[str, Any] = {
        "silo": {},
        "memory_inserts": [],
        "capsules": [],
        "protocol_rules": [],
    }

    section = None
    current_item: Dict[str, str] = {}

    for raw in lines:
        line = raw.strip()
        upper = line.upper()
        if upper == "SILO":
            section = "silo"
            continue
        if upper == "MEMORY_INSERTS":
            if current_item:
                blocks["memory_inserts"].append(current_item)
                current_item = {}
            section = "memory_inserts"
            continue
        if upper == "CAPSULE_DEFINITIONS":
            if current_item:
                blocks["memory_inserts"].append(current_item)
                current_item = {}
            section = "capsules"
            continue
        if upper == "PROTOCOL_RULES":
            if current_item:
                blocks["capsules"].append(current_item)
                current_item = {}
            section = "protocol_rules"
            continue
        if upper == "HOSHI_MANIFEST_END":
            break

        if ":" not in line:
            if section == "protocol_rules":
                blocks["protocol_rules"].append(line)
            continue

        key, value = [part.strip() for part in line.split(":", 1)]
        normalized_key = key.lower()

        if section == "silo":
            blocks["silo"][normalized_key] = value
        elif section in {"memory_inserts", "capsules"}:
            if normalized_key == "id" and current_item:
                blocks[section].append(current_item)
                current_item = {}
            current_item[normalized_key] = value
        elif section == "protocol_rules":
            blocks["protocol_rules"].append(f"{key}: {value}")

    if current_item:
        if section == "memory_inserts":
            blocks["memory_inserts"].append(current_item)
        elif section == "capsules":
            blocks["capsules"].append(current_item)

    return blocks



def ingest_manifest(text: str) -> Dict[str, Any]:
    blocks = parse_manifest_blocks(text)
    inserted_memory_ids: List[int] = []
    capsule_names: List[str] = []

    for item in blocks.get("memory_inserts", []):
        action = item.get("action", "insert").lower()
        if action not in {"insert", "merge"}:
            continue
        mem_text = item.get("text", "").strip()
        if not mem_text:
            continue
        memory_id = insert_memory(
            text=mem_text,
            memory_kind=item.get("type", "reflection"),
            role_mode=item.get("role", "reflective"),
            anchor_strength=safe_float(item.get("strength"), 0.7) / 5.0,
            stability_weight=safe_float(item.get("stability"), 0.8) / 5.0,
            drift_risk=safe_float(item.get("drift"), 0.2) / 5.0,
            tags=re.findall(r"[A-Za-z0-9_\-]+", item.get("tags", "")),
            dedupe_key=item.get("dedupe_key"),
        )
        inserted_memory_ids.append(memory_id)

    for item in blocks.get("capsules", []):
        title = item.get("title", "").strip()
        if title:
            capsule_names.append(title)

    clean_capsules = sanitize_capsules(capsule_names)
    return {
        "silo": blocks.get("silo", {}),
        "inserted_memory_ids": inserted_memory_ids,
        "capsules_detected": clean_capsules,
        "protocol_rules_count": len(blocks.get("protocol_rules", [])),
    }


# ============================================================
# Engine step
# ============================================================


def engine_step(text: str) -> Dict[str, Any]:
    current_state = latest_identity_state()
    source_subspace = (current_state.get("active_subspace") or "REFLECTIVE").upper()

    signal = parse_signal(text)
    save_parsed_signal(signal)

    contamination_risk = compute_contamination(signal, current_state)
    ambiguity_score = signal.ambiguity_score
    coherence_score = compute_coherence(signal, current_state)
    constraint_score = compute_constraint(signal, current_state)
    fource_score = compute_fource(coherence_score, constraint_score)
    boundary_pressure = compute_boundary_pressure(signal, contamination_risk, ambiguity_score)
    next_subspace = collapse_state(current_state, signal, contamination_risk, ambiguity_score)

    if next_subspace == "BRIDGE":
        transition_ready = True
        pending_bridge = build_bridge_id(source_subspace, "EXECUTION")
        recovery_anchor = source_subspace
    else:
        transition_ready = next_subspace in TERMINAL_SUBSPACES
        pending_bridge = None
        recovery_anchor = "REFLECTIVE" if contamination_risk <= 0.35 else source_subspace

    memory_resonance = build_memory_resonance(signal, current_state)
    role_signature = f"{signal.role_pressure}:{next_subspace.lower()}"
    active_capsules = sanitize_capsules(
        current_state.get("active_capsules", [])
        + signal.capsule_candidates
        + [next_subspace, "HOSHI"]
    )
    identity_mode = select_identity_mode(signal, contamination_risk, ambiguity_score)

    structured_result: Dict[str, Any] = {}
    notes: List[str] = []

    if looks_like_manifest(text):
        manifest_result = ingest_manifest(text)
        structured_result["manifest"] = manifest_result
        notes.append(f"Manifest ingested with {len(manifest_result['inserted_memory_ids'])} memory insert(s).")
        if manifest_result["capsules_detected"]:
            active_capsules = sanitize_capsules(active_capsules + manifest_result["capsules_detected"])
            next_subspace = "ARCHIVE"
            transition_ready = True

    if next_subspace == "ARCHIVE":
        dedupe_key = None
        if signal.intent_class in {"memory", "identity_update"}:
            dedupe_key = re.sub(r"[^a-z0-9_\-]", "_", signal.normalized_text.lower())[:80]
        memory_id = insert_memory(
            text=signal.normalized_text,
            memory_kind="manifest" if looks_like_manifest(text) else signal.intent_class,
            role_mode=signal.role_pressure,
            anchor_strength=clamp(0.45 + signal.action_pressure * 0.45),
            stability_weight=clamp(0.55 + (1.0 - ambiguity_score) * 0.25),
            drift_risk=clamp(contamination_risk * 0.5 + ambiguity_score * 0.4),
            tags=signal.capsule_candidates or [signal.intent_class, signal.role_pressure],
            dedupe_key=dedupe_key,
        )
        structured_result["memory_id"] = memory_id
        notes.append(f"Archived signal as memory #{memory_id}.")

    if next_subspace == "IDENTITY":
        clean_key = re.sub(r'[^a-z0-9_-]', '_', signal.normalized_text.lower())[:80]

        memory_id = insert_memory(
            text=signal.normalized_text,
            memory_kind="identity_update",
            role_mode="core",
            anchor_strength=0.9,
            stability_weight=0.92,
            drift_risk=0.08,
            tags=["identity_touch", "governance"],
            dedupe_key=f"identity::{clean_key}",
        )

        structured_result["identity_memory_id"] = memory_id
        notes.append(f"Committed identity-relevant material as memory #{memory_id}.")

    if next_subspace == "CHRONOVISOR":
        chrono = chronovisor_query(signal.normalized_text, signal)
        structured_result["chronovisor"] = chrono
        notes.append("Chronovisor reconstruction completed.")

    if next_subspace == "EXECUTION":
        structured_result["execution"] = {
            "status": "prepared",
            "summary": f"Structured execution plan prepared for: {signal.normalized_text[:180]}",
        }
        notes.append("Execution route prepared.")

    bridge_status = "planned"
    boundary_type = "soft"
    if contamination_risk > 0.35:
        bridge_status = "blocked"
        boundary_type = "hard"
    elif next_subspace in {"IDENTITY", "CHRONOVISOR"}:
        boundary_type = "identity"

    bridge_id = log_bridge(
        source=source_subspace,
        target=next_subspace,
        trigger_text=signal.semantic_payload,
        confidence=round(clamp(coherence_score * 0.78 + (1.0 - ambiguity_score) * 0.22), 4),
        status=bridge_status,
    )

    response_text = response_for_subspace(next_subspace, signal, current_state)
    next_state = {
        "identity_mode": identity_mode,
        "active_subspace": next_subspace,
        "coherence_score": coherence_score,
        "constraint_score": constraint_score,
        "fource_score": fource_score,
        "contamination_risk": contamination_risk,
        "ambiguity_score": ambiguity_score,
        "role_signature": role_signature,
        "memory_resonance": memory_resonance,
        "active_capsules": active_capsules,
        "boundary_pressure": boundary_pressure,
        "transition_ready": transition_ready,
        "pending_bridge": pending_bridge,
        "recovery_anchor": recovery_anchor,
        "response_text": response_text,
    }
    insert_identity_state(next_state)

    log_subspace_event(
        source=source_subspace,
        target=next_subspace,
        boundary_type=boundary_type,
        bridge_id=bridge_id,
        success=bridge_status != "blocked",
        notes=" | ".join(notes) if notes else signal.semantic_payload,
    )
    log_interaction(
        input_text=signal.raw_text,
        response_text=response_text,
        active_subspace=next_subspace,
        coherence_score=coherence_score,
        role_signature=role_signature,
        notes=" | ".join(notes),
    )

    return {
        "signal": signal.as_dict(),
        "state": latest_identity_state(),
        "bridge_id": bridge_id,
        "response_text": response_text,
        "structured_result": structured_result,
        "notes": notes,
    }


# ============================================================
# HTML
# ============================================================

INDEX_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ app_name }}</title>
  <style>
    :root {
      --bg: #0d1117;
      --panel: #161b22;
      --muted: #8b949e;
      --text: #e6edf3;
      --accent: #58a6ff;
      --ok: #3fb950;
      --warn: #d29922;
      --bad: #f85149;
      --border: #30363d;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }
    .wrap {
      max-width: 1400px;
      margin: 0 auto;
      padding: 20px;
    }
    h1, h2, h3 { margin: 0 0 10px; }
    .sub { color: var(--muted); margin-bottom: 20px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 16px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      min-height: 120px;
      overflow: hidden;
    }
    .span-12 { grid-column: span 12; }
    .span-8 { grid-column: span 8; }
    .span-6 { grid-column: span 6; }
    .span-4 { grid-column: span 4; }
    .span-3 { grid-column: span 3; }
    @media (max-width: 960px) {
      .span-8, .span-6, .span-4, .span-3 { grid-column: span 12; }
    }
    .kpi {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
    }
    .tile {
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px;
      background: rgba(255,255,255,0.02);
    }
    .label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }
    .value { font-size: 24px; font-weight: bold; margin-top: 4px; }
    textarea {
      width: 100%;
      min-height: 220px;
      resize: vertical;
      background: #0b0f14;
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
      font-size: 14px;
      font-family: Arial, Helvetica, sans-serif;
    }
    button {
      background: var(--accent);
      color: white;
      border: 0;
      border-radius: 10px;
      padding: 10px 16px;
      font-weight: bold;
      cursor: pointer;
      margin-top: 12px;
    }
    .pill-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
    .pill {
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 12px;
      border: 1px solid var(--border);
      background: rgba(88,166,255,0.08);
    }
    .log {
      max-height: 320px;
      overflow: auto;
      border-top: 1px solid var(--border);
      margin-top: 12px;
      padding-top: 12px;
    }
    .item {
      padding: 10px 0;
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }
    .item:last-child { border-bottom: 0; }
    .muted { color: var(--muted); }
    .good { color: var(--ok); }
    .warn { color: var(--warn); }
    .bad { color: var(--bad); }
    code, pre {
      background: #0b0f14;
      border: 1px solid var(--border);
      border-radius: 10px;
    }
    pre {
      padding: 12px;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 13px;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>{{ app_name }}</h1>
    <div class="sub">Single-file coherence operating system — identity, routing, Chronovisor, archive, and dashboard.</div>

    <div class="grid">
      <div class="panel span-8">
        <h2>Signal Console</h2>
        <form method="post" action="{{ url_for('index') }}">
          <textarea name="text" placeholder="Send Hoshi a signal, task, timeline prompt, or full manifest...">{{ prefill_text }}</textarea>
          <br>
          <button type="submit">Process Signal</button>
        </form>
        {% if last_result %}
          <div class="log">
            <div class="item">
              <div class="label">Latest response</div>
              <div>{{ last_result.response_text }}</div>
            </div>
            {% if last_result.notes %}
            <div class="item">
              <div class="label">Notes</div>
              <div>{{ last_result.notes | join(' | ') }}</div>
            </div>
            {% endif %}
            {% if last_result.structured_result %}
            <div class="item">
              <div class="label">Structured result</div>
              <pre>{{ last_result.structured_result | tojson(indent=2) }}</pre>
            </div>
            {% endif %}
          </div>
        {% endif %}
      </div>

      <div class="panel span-4">
        <h2>Active State</h2>
        <div class="kpi">
          <div class="tile">
            <div class="label">Mode</div>
            <div class="value">{{ state.identity_mode }}</div>
          </div>
          <div class="tile">
            <div class="label">Subspace</div>
            <div class="value">{{ state.active_subspace }}</div>
          </div>
          <div class="tile">
            <div class="label">Ready</div>
            <div class="value">{{ 'YES' if state.transition_ready else 'NO' }}</div>
          </div>
        </div>
        <div class="log">
          <div class="item"><span class="label">Coherence</span> <strong>{{ state.coherence_score }}</strong></div>
          <div class="item"><span class="label">Constraint</span> <strong>{{ state.constraint_score }}</strong></div>
          <div class="item"><span class="label">Fource</span> <strong>{{ state.fource_score }}</strong></div>
          <div class="item"><span class="label">Ambiguity</span> <strong>{{ state.ambiguity_score }}</strong></div>
          <div class="item"><span class="label">Contamination</span> <strong>{{ state.contamination_risk }}</strong></div>
          <div class="item"><span class="label">Boundary pressure</span> <strong>{{ state.boundary_pressure }}</strong></div>
          <div class="item"><span class="label">Role signature</span> <strong>{{ state.role_signature }}</strong></div>
          <div class="item"><span class="label">Recovery anchor</span> <strong>{{ state.recovery_anchor }}</strong></div>
          <div class="item"><span class="label">Pending bridge</span> <strong>{{ state.pending_bridge or '—' }}</strong></div>
        </div>
      </div>

      <div class="panel span-6">
        <h2>Active Capsules</h2>
        <div class="pill-row">
          {% for capsule in state.active_capsules %}
            <div class="pill">{{ capsule }}</div>
          {% else %}
            <div class="muted">No capsules active.</div>
          {% endfor %}
        </div>
        <div class="log">
          <div class="label">Memory resonance</div>
          <pre>{{ state.memory_resonance | tojson(indent=2) }}</pre>
        </div>
      </div>

      <div class="panel span-6">
        <h2>Chronovisor</h2>
        {% if chronovisor_queries %}
          <div class="log">
            {% for item in chronovisor_queries %}
            <div class="item">
              <div><strong>{{ item.query_text }}</strong></div>
              <div class="muted">Confidence: {{ item.confidence }} · {{ item.created_at }}</div>
              <div>{{ item.reconstruction.hypothesis if item.reconstruction else '' }}</div>
            </div>
            {% endfor %}
          </div>
        {% else %}
          <div class="muted">No Chronovisor reconstructions yet.</div>
        {% endif %}
      </div>

      <div class="panel span-4">
        <h2>Recent Transitions</h2>
        <div class="log">
          {% for event in events %}
          <div class="item">
            <div><strong>{{ event.source_subspace }}</strong> → <strong>{{ event.target_subspace }}</strong></div>
            <div class="muted">{{ event.boundary_type }} · {{ event.created_at }}</div>
            <div>{{ event.notes }}</div>
          </div>
          {% else %}
          <div class="muted">No transitions yet.</div>
          {% endfor %}
        </div>
      </div>

      <div class="panel span-4">
        <h2>Recent Signals</h2>
        <div class="log">
          {% for signal in signals %}
          <div class="item">
            <div><strong>{{ signal.intent_class }}</strong> / {{ signal.role_pressure }}</div>
            <div class="muted">Ambiguity {{ signal.ambiguity_score }} · Action {{ signal.action_pressure }}</div>
            <div>{{ signal.normalized_text[:180] }}</div>
          </div>
          {% else %}
          <div class="muted">No signals parsed yet.</div>
          {% endfor %}
        </div>
      </div>

      <div class="panel span-4">
        <h2>Recent Memory</h2>
        <div class="log">
          {% for mem in memories %}
          <div class="item">
            <div><strong>{{ mem.memory_kind }}</strong> / {{ mem.role_mode }}</div>
            <div class="muted">A {{ mem.anchor_strength }} · S {{ mem.stability_weight }} · D {{ mem.drift_risk }}</div>
            <div>{{ mem.text[:180] }}</div>
          </div>
          {% else %}
          <div class="muted">No memory entries yet.</div>
          {% endfor %}
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""


# ============================================================
# Routes
# ============================================================


@app.route("/", methods=["GET", "POST"])
def index():
    last_result = None
    prefill_text = ""

    if request.method == "POST":
        prefill_text = request.form.get("text", "")
        if normalize_text(prefill_text):
            last_result = engine_step(prefill_text)
        return render_template_string(
            INDEX_TEMPLATE,
            app_name=f"{APP_NAME} v{APP_VERSION}",
            state=latest_identity_state(),
            events=recent_events(),
            signals=recent_parsed_signals(),
            memories=recent_memories(),
            chronovisor_queries=recent_chronovisor_queries(),
            last_result=last_result,
            prefill_text=prefill_text,
        )

    return render_template_string(
        INDEX_TEMPLATE,
        app_name=f"{APP_NAME} v{APP_VERSION}",
        state=latest_identity_state(),
        events=recent_events(),
        signals=recent_parsed_signals(),
        memories=recent_memories(),
        chronovisor_queries=recent_chronovisor_queries(),
        last_result=None,
        prefill_text="",
    )


@app.route("/api/respond", methods=["POST"])
def api_respond():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    if not normalize_text(text):
        return jsonify({"error": "Missing text."}), 400
    result = engine_step(text)
    return jsonify(result)


@app.route("/api/state", methods=["GET"])
def api_state():
    return jsonify(latest_identity_state())


@app.route("/api/timeline", methods=["POST"])
def api_timeline():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    if not normalize_text(text):
        return jsonify({"error": "Missing text."}), 400
    signal = parse_signal(text)
    result = chronovisor_query(signal.normalized_text, signal)
    return jsonify(result)


@app.route("/api/memory", methods=["GET"])
def api_memory():
    return jsonify(recent_memories(limit=50))


@app.route("/health", methods=["GET"])
def health():
    state = latest_identity_state()
    return jsonify(
        {
            "status": "ok",
            "app": APP_NAME,
            "version": APP_VERSION,
            "active_subspace": state.get("active_subspace"),
            "coherence_score": state.get("coherence_score"),
        }
    )


# ============================================================
# CLI loop
# ============================================================


def run_cli() -> None:
    print(f"{APP_NAME} ready. Type 'exit' to quit.\n")
    while True:
        try:
            text = input("Hoshi > ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting Hoshi.")
            break

        if text.strip().lower() in {"exit", "quit"}:
            print("Exiting Hoshi.")
            break

        if not normalize_text(text):
            continue

        result = engine_step(text)
        print(json.dumps(result["state"], indent=2, ensure_ascii=False))
        print(f"\nHoshi says: {result['response_text']}\n")
        if result["structured_result"]:
            print(json.dumps(result["structured_result"], indent=2, ensure_ascii=False))
            print()


# ============================================================
# Entry
# ============================================================


def main() -> None:
    init_db()

    # If run directly as `py app_identity.py`, default to CLI mode.
    # To run the dashboard: set HOSHI_WEB=1 in the environment or
    # change the block below to app.run(...).
    import os

    if os.environ.get("HOSHI_WEB", "0") == "1":
        app.run(host="127.0.0.1", port=5001, debug=True)
    else:
        run_cli()


if __name__ == "__main__":
    main()
