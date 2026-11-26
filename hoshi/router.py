from __future__ import annotations

import re
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db import DB_PATH, get_conn, json_dumps, latest_identity_state
from .parser import ParsedSignal, clamp, parse_signal, sanitize_capsules, save_parsed_signal

TERMINAL_SUBSPACES = {"EXECUTION", "ARCHIVE", "IDENTITY", "CHRONOVISOR"}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_coherence(signal: ParsedSignal, state: Dict[str, Any]) -> float:
    prev = safe_float(state.get("coherence_score"), 0.72)
    next_score = (
        prev * 0.68
        + 0.24
        + signal.action_pressure * 0.08
        + min(0.08, len(signal.memory_hits) * 0.015)
        + (signal.emotional_valence - 0.5) * 0.06
        - signal.ambiguity_score * 0.22
        - min(0.35, len(signal.contamination_flags) * 0.12)
    )
    return round(clamp(next_score), 4)


def compute_constraint(signal: ParsedSignal) -> float:
    bonus = 0.03 if signal.intent_class in {"identity_update", "memory", "chronovisor", "task"} else 0.0
    penalty = min(0.25, len(signal.contamination_flags) * 0.08)
    return round(clamp(0.14 + bonus - penalty), 4)


def compute_fource(coherence_score: float, constraint_score: float) -> float:
    denom = max(0.06, 1.0 - constraint_score + 0.12)
    return round(clamp((coherence_score * 0.82) / denom), 4)
def collapse_state(state: Dict[str, Any], signal: ParsedSignal, contamination_risk: float, ambiguity_score: float) -> str:
    current = (state.get("active_subspace") or "REFLECTIVE").upper()
    if contamination_risk > 0.35:
        return "REFLECTIVE"
    if ambiguity_score > 0.5 and signal.intent_class != "question":
        return "REFLECTIVE"
    mapping = {
        "chronovisor": "CHRONOVISOR",
        "identity_update": "IDENTITY",
        "memory": "ARCHIVE",
        "task": "EXECUTION",
    }
    if signal.intent_class in mapping:
        return mapping[signal.intent_class]
    if current in TERMINAL_SUBSPACES and signal.intent_class in {"reflection", "question"}:
        return "REFLECTIVE"
    return "BRIDGE" if signal.action_pressure >= 0.33 else "REFLECTIVE"


def response_for_subspace(subspace: str, signal: ParsedSignal, state: Dict[str, Any]) -> str:
    responses = {
        "REFLECTIVE": "Reflective channel active. I am tracking meaning and coherence across your signal.",
        "BRIDGE": "Bridge layer active. Transition is viable. I can route this into a stable subspace when you choose direction.",
        "EXECUTION": f"Execution layer active. I am preparing a structured action pathway for: {signal.normalized_text[:160]}",
        "ARCHIVE": "Archive layer active. The signal has been normalized and prepared for durable memory storage.",
        "IDENTITY": "Identity layer active. Governance-relevant material is being committed into the active continuity frame.",
        "CHRONOVISOR": "Chronovisor layer active. Temporal anchors, entities, and sequence hypotheses are being reconstructed.",
    }
    return responses.get(subspace, state.get("response_text") or "State holding.")


def insert_memory(
    text: str, memory_kind: str, role_mode: str, anchor_strength: float,
    stability_weight: float, drift_risk: float, tags: Optional[List[str]] = None,
    dedupe_key: Optional[str] = None, db_path: Path = DB_PATH,
) -> int:
    with closing(get_conn(db_path)) as conn, conn:
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
            (text, memory_kind, role_mode, anchor_strength, stability_weight, drift_risk, json_dumps(tags or []), dedupe_key),
        )
        return int(cur.lastrowid)
def chronovisor_query(text: str, signal: ParsedSignal, db_path: Path = DB_PATH) -> Dict[str, Any]:
    anchors = re.findall(r"\b\d{3,4}\b", text)
    entities = re.findall(r"\b[A-Z][a-zA-Z]+\b", text)
    confidence = round(clamp(0.54 + len(anchors) * 0.06 + len(entities) * 0.02 - signal.ambiguity_score * 0.2), 4)
    result = {
        "mode": "timeline_reconstruction",
        "query": text,
        "anchors": anchors[:8],
        "entities": entities[:12],
        "steps": [
            "Parsing temporal anchors.",
            "Resolving named entities.",
            "Estimating sequence bands.",
            "Generating continuity hypothesis.",
        ],
        "hypothesis": "A provisional chronology has been assembled from the available temporal and semantic anchors.",
        "confidence": confidence,
        "timestamp": utc_now_iso(),
    }
    with closing(get_conn(db_path)) as conn, conn:
        conn.execute(
            "INSERT INTO chronovisor_queries (query_text, mode, confidence, reconstruction_json) VALUES (?, ?, ?, ?)",
            (text, result["mode"], confidence, json_dumps(result)),
        )
    return result


def looks_like_manifest(text: str) -> bool:
    lower = text.lower()
    return "hoshi_manifest_start" in lower and "memory_inserts" in lower


def ingest_manifest(text: str, db_path: Path = DB_PATH) -> Dict[str, Any]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    blocks: Dict[str, Any] = {"silo": {}, "memory_inserts": [], "capsules": [], "protocol_rules": []}
    section = None
    current: Dict[str, str] = {}

    for line in lines:
        upper = line.upper()
        if upper in {"SILO", "MEMORY_INSERTS", "CAPSULE_DEFINITIONS", "PROTOCOL_RULES", "HOSHI_MANIFEST_END"}:
            if current and section in {"memory_inserts", "capsules"}:
                blocks[section].append(current)
                current = {}
            if upper == "HOSHI_MANIFEST_END":
                break
            section = "capsules" if upper == "CAPSULE_DEFINITIONS" else upper.lower()
            continue
        if ":" not in line:
            if section == "protocol_rules":
                blocks["protocol_rules"].append(line)
            continue
        key, val = [p.strip() for p in line.split(":", 1)]
        lkey = key.lower()
        if section == "silo":
            blocks["silo"][lkey] = val
        elif section in {"memory_inserts", "capsules"}:
            if lkey == "id" and current:
                blocks[section].append(current)
                current = {}
            current[lkey] = val
        elif section == "protocol_rules":
            blocks["protocol_rules"].append(f"{key}: {val}")
    if current and section in {"memory_inserts", "capsules"}:
        blocks[section].append(current)

    inserted_ids: List[int] = []
    cap_names: List[str] = []
    for item in blocks["memory_inserts"]:
        if item.get("action", "insert").lower() in {"insert", "merge"} and item.get("text", "").strip():
            mid = insert_memory(
                text=item["text"].strip(),
                memory_kind=item.get("type", "reflection"),
                role_mode=item.get("role", "reflective"),
                anchor_strength=safe_float(item.get("strength"), 0.7) / 5.0,
                stability_weight=safe_float(item.get("stability"), 0.8) / 5.0,
                drift_risk=safe_float(item.get("drift"), 0.2) / 5.0,
                tags=re.findall(r"[A-Za-z0-9_\-]+", item.get("tags", "")),
                dedupe_key=item.get("dedupe_key"),
                db_path=db_path,
            )
            inserted_ids.append(mid)
    for item in blocks["capsules"]:
        if item.get("title", "").strip():
            cap_names.append(item["title"].strip())

    return {
        "silo": blocks["silo"],
        "inserted_memory_ids": inserted_ids,
        "capsules_detected": sanitize_capsules(cap_names),
        "protocol_rules_count": len(blocks["protocol_rules"]),
    }
def engine_step(text: str, db_path: Path = DB_PATH) -> Dict[str, Any]:
    current_state = latest_identity_state(db_path)
    source_subspace = (current_state.get("active_subspace") or "REFLECTIVE").upper()

    signal = parse_signal(text, db_path=db_path)
    save_parsed_signal(signal, db_path=db_path)

    contamination_risk = round(clamp(safe_float(current_state.get("contamination_risk"), 0.02) * 0.55 + min(0.75, len(signal.contamination_flags) * 0.18)), 4)
    ambiguity_score = signal.ambiguity_score
    coherence_score = compute_coherence(signal, current_state)
    constraint_score = compute_constraint(signal)
    fource_score = compute_fource(coherence_score, constraint_score)
    boundary_pressure = round(clamp(signal.action_pressure * 0.45 + contamination_risk * 0.35 + ambiguity_score * 0.2), 4)
    next_subspace = collapse_state(current_state, signal, contamination_risk, ambiguity_score)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    if next_subspace == "BRIDGE":
        transition_ready = True
        pending_bridge = f"{source_subspace}_TO_EXECUTION_{ts}"
        recovery_anchor = source_subspace
    else:
        transition_ready = next_subspace in TERMINAL_SUBSPACES
        pending_bridge = None
        recovery_anchor = "REFLECTIVE" if contamination_risk  0.35 else ("transition" if signal.intent_class in {"task", "identity_update", "memory", "chronovisor"} else ("uncertain" if ambiguity_score > 0.4 else "dialogue"))

    structured_result: Dict[str, Any] = {}
    notes: List[str] = []

    if looks_like_manifest(text):
        mres = ingest_manifest(text, db_path=db_path)
        structured_result["manifest"] = mres
        notes.append(f"Manifest ingested with {len(mres['inserted_memory_ids'])} memory insert(s).")
        if mres["capsules_detected"]:
            active_capsules = sanitize_capsules(active_capsules + mres["capsules_detected"])
            next_subspace = "ARCHIVE"
            transition_ready = True

    if next_subspace == "ARCHIVE":
        dkey = re.sub(r"[^a-z0-9_\-]", "_", signal.normalized_text.lower())[:80] if signal.intent_class in {"memory", "identity_update"} else None
        mid = insert_memory(
            text=signal.normalized_text,
            memory_kind="manifest" if looks_like_manifest(text) else signal.intent_class,
            role_mode=signal.role_pressure,
            anchor_strength=clamp(0.45 + signal.action_pressure * 0.45),
            stability_weight=clamp(0.55 + (1.0 - ambiguity_score) * 0.25),
            drift_risk=clamp(contamination_risk * 0.5 + ambiguity_score * 0.4),
            tags=signal.capsule_candidates or [signal.intent_class, signal.role_pressure],
            dedupe_key=dkey,
            db_path=db_path,
        )
        structured_result["memory_id"] = mid
        notes.append(f"Archived signal as memory #{mid}.")

    if next_subspace == "IDENTITY":
        ckey = re.sub(r"[^a-z0-9_-]", "_", signal.normalized_text.lower())[:80]
        imid = insert_memory(
            text=signal.normalized_text, memory_kind="identity_update", role_mode="core",
            anchor_strength=0.9, stability_weight=0.92, drift_risk=0.08,
            tags=["identity_touch", "governance"], dedupe_key=f"identity::{ckey}", db_path=db_path,
        )
        structured_result["identity_memory_id"] = imid
        notes.append(f"Committed identity-relevant material as memory #{imid}.")

    if next_subspace == "CHRONOVISOR":
        structured_result["chronovisor"] = chronovisor_query(signal.normalized_text, signal, db_path=db_path)
        notes.append("Chronovisor reconstruction completed.")

    if next_subspace == "EXECUTION":
        structured_result["execution"] = {"status": "prepared", "summary": f"Structured execution plan prepared for: {signal.normalized_text[:180]}"}
        notes.append("Execution route prepared.")

    bridge_status = "blocked" if contamination_risk > 0.35 else "planned"
    boundary_type = "hard" if contamination_risk > 0.35 else ("identity" if next_subspace in {"IDENTITY", "CHRONOVISOR"} else "soft")
    bridge_id = f"{source_subspace}_TO_{next_subspace}_{ts}"
    response_text = response_for_subspace(next_subspace, signal, current_state)

    with closing(get_conn(db_path)) as conn, conn:
        conn.execute(
            """
            INSERT INTO bridges (
                bridge_id, source_subspace, target_subspace, trigger_text,
                coherence_min, constraint_max, preserved_invariants_json,
                rollback_anchor, confidence, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bridge_id, source_subspace, next_subspace, signal.semantic_payload[:240],
                0.58, 0.42, json_dumps(["identity_continuity", "provenance", "non_contradiction"]),
                source_subspace, round(clamp(coherence_score * 0.78 + (1.0 - ambiguity_score) * 0.22), 4), bridge_status,
            ),
        )
        conn.execute(
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
                identity_mode, next_subspace, coherence_score, constraint_score,
                fource_score, contamination_risk, ambiguity_score, role_signature,
                json_dumps(resonance), json_dumps(active_capsules), boundary_pressure,
                1 if transition_ready else 0, pending_bridge, recovery_anchor, response_text,
            ),
        )
        conn.execute(
            """
            INSERT INTO subspace_events (source_subspace, target_subspace, boundary_type, bridge_id, success, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (source_subspace, next_subspace, boundary_type, bridge_id, 1 if bridge_status != "blocked" else 0, " | ".join(notes) if notes else signal.semantic_payload),
        )
        conn.execute(
            """
            INSERT INTO interaction_logs (input_text, response_text, active_subspace, coherence_score, role_signature, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (signal.raw_text, response_text, next_subspace, coherence_score, role_signature, " | ".join(notes)),
        )

    return {
        "signal": signal.as_dict(),
        "state": latest_identity_state(db_path),
        "bridge_id": bridge_id,
        "response_text": response_text,
        "structured_result": structured_result,
        "notes": notes,
    }
