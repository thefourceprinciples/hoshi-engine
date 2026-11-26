from __future__ import annotations

import re
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .db import DB_PATH, get_conn, json_dumps


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def sanitize_capsules(capsules: List[Any]) -> List[str]:
    clean: List[str] = []
    for item in capsules:
        if not isinstance(item, str):
            continue
        token = re.sub(r"[^A-Z0-9_\-]", "", item.upper()).strip("_-")
        if token and len(token) <= 40 and token not in clean:
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
    found = [cap for cap, kws in CAPSULE_KEYWORDS.items() if any(kw in lower for kw in kws)]
    return sanitize_capsules(found)


def detect_contamination(text: str) -> List[str]:
    return [pat for pat in CONTAMINATION_PATTERNS if re.search(pat, text, flags=re.IGNORECASE)]


def estimate_emotional_valence(text: str) -> float:
    lower = text.lower()
    pos = sum(lower.count(w) for w in ["good", "love", "trust", "thanks", "friend", "clear"])
    neg = sum(lower.count(w) for w in ["lost", "confused", "overwhelmed", "bad", "hurt", "afraid"])
    raw = (pos - neg) / max(1, pos + neg + 1)
    return round(clamp((raw + 1) / 2), 4)


def estimate_ambiguity(text: str) -> float:
    lower = text.lower()
    markers = sum(lower.count(m) for m in AMBIGUITY_MARKERS)
    short_pen = 0.15 if len(lower.split()) < 4 else 0.0
    return round(min(1.0, 0.08 * markers + short_pen), 4)


def estimate_action_pressure(text: str, intent: str) -> float:
    lower = text.lower()
    hits = sum(lower.count(w) for w in ["build", "do", "make", "write", "generate", "fix", "run"])
    bonus = 0.25 if intent in {"task", "identity_update", "memory", "chronovisor"} else 0.05
    return round(min(1.0, 0.08 * hits + bonus), 4)


def recent_memory_hits(text: str, limit: int = 5, db_path: Path = DB_PATH) -> List[str]:
    tokens = {t for t in re.findall(r"[a-zA-Z0-9_\-]{4,}", text.lower())}
    if not tokens:
        return []
    with closing(get_conn(db_path)) as conn:
        rows = conn.execute("SELECT text FROM memory_entries ORDER BY id DESC LIMIT 50").fetchall()
    hits: List[str] = []
    for row in rows:
        mem_text = row["text"]
        if sum(1 for tok in tokens if tok in mem_text.lower()) >= 2:
            hits.append(mem_text[:120])
        if len(hits) >= limit:
            break
    return hits


def parse_signal(text: str, db_path: Path = DB_PATH) -> ParsedSignal:
    raw_text = text or ""
    normalized = normalize_text(raw_text)
    intent = detect_intent(normalized)
    role = detect_role(normalized)
    anchors = dedupe_preserve_order(re.findall(r"\b[A-Z][A-Z0-9_\-]{2,}\b", raw_text))[:8]
    return ParsedSignal(
        raw_text=raw_text,
        normalized_text=normalized,
        semantic_payload=f"intent={intent}; role={role}; length={len(normalized)}",
        intent_class=intent,
        emotional_valence=estimate_emotional_valence(normalized),
        role_pressure=role,
        symbolic_anchors=anchors,
        memory_hits=recent_memory_hits(normalized, db_path=db_path),
        capsule_candidates=detect_capsules(normalized),
        contamination_flags=detect_contamination(raw_text),
        ambiguity_score=estimate_ambiguity(normalized),
        action_pressure=estimate_action_pressure(normalized, intent),
    )


def save_parsed_signal(signal: ParsedSignal, db_path: Path = DB_PATH) -> int:
    with closing(get_conn(db_path)) as conn, conn:
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
                signal.raw_text, signal.normalized_text, signal.semantic_payload,
                signal.intent_class, signal.emotional_valence, signal.role_pressure,
                json_dumps(signal.symbolic_anchors), json_dumps(signal.memory_hits),
                json_dumps(signal.capsule_candidates), json_dumps(signal.contamination_flags),
                signal.ambiguity_score, signal.action_pressure,
            ),
        )
        return int(cur.lastrowid)
