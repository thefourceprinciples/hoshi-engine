from __future__ import annotations

import re
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db import DB_PATH, get_conn, json_dumps, json_loads

INITIAL_SEEDS = [
    ("FR-001", "Fource", "ROOT", "canonical", "Fource is the coherence principle describing stable pattern emergence under constraint.", "Return to the coherence seed."),
    ("FR-002", "UFAP", "ROOT", "canonical", "Coherence can be evaluated through Origin, Expression, History/Integration, and Extension/Resonance.", "Return to C = O * E * H * X."),
    ("FR-003", "Coherence Under Constraint / CUC", "ROOT", "canonical", "Structure persists when coherence survives constraint.", "Return to coherence under constraint."),
    ("FR-004", "Apophatic Dynamics", "CLEARING", "rooted", "Remove false structure to reveal residual truth, uncertainty, and hidden pattern.", "Clear the field."),
    ("FR-005", "Cataphatic Dynamics", "CLEARING", "rooted", "Name, build, and preserve what survives clearing.", "Raise the form."),
    ("FR-006", "Darkness Functional", "CLEARING", "rooted", "The darkness functional tracks residuals, gaps, distortions, and unmodeled structure after subtraction.", "Read the remainder."),
    ("FR-007", "FourceLang", "KERNEL", "sprout", "FourceLang is the readable command/markup layer for declaring nodes, memories, modes, rules, capsules, and kernel operations.", "Speak the pattern."),
    ("FR-008", "HoshiCore Kernel", "KERNEL", "rooted", "HoshiCore is the small lawful center that governs memory, routing, identity, quarantine, audit, and continuity.", "Return to the kernel."),
    ("FR-009", "CAS", "KERNEL", "canonical", "CAS converts living conversation and long-form projects into minimalist, ultra-compacted Steward datasheets.", "Archive the growth."),
    ("FR-010", "KOS", "KERNEL", "rooted", "KOS organizes knowledge through Thread -> Extraction -> Node -> Link -> Artifact.", "Operate the archive."),
    ("FR-011", "Chronovisor", "ATLAS", "rooted", "The Chronovisor is a living atlas for evidence, claims, contradictions, scenarios, and civilizational/historical mapping.", "Open the living atlas."),
    ("FR-012", "UCMS", "ATLAS", "canonical", "UCMS maps phenomena across layered coordinates: geospatial, historical, cultural, material, symbolic, ecological, and systemic.", "Map the whole field."),
    ("FR-013", "Framework Garden Protocol", "KERNEL", "canonical", "Frameworks are living seeds that must be watered, versioned, linked, harvested, and returned to the hearth.", "Start the garden."),
    ("FR-014", "Framework Registry", "KERNEL", "rooted", "Every mature framework receives a stable number, summary, source, version, and rehydration path.", "Number the garden."),
    ("FR-015", "Materials Atlas", "MATERIAL", "rooted", "Materials can be mapped by composition, structure, behavior, state transitions, constraints, and coherence functions.", "Read the material field."),
    ("FR-016", "HTE", "MATERIAL", "canonical", "Atomic number modulo 12 can be used as a harmonic coordinate system for speculative material pattern mapping.", "Tune the elements."),
    ("FR-017", "HTE Triple Engine", "MATERIAL", "rooted", "The HTE Triple Engine is the cockpit for material casework, harmonic state detection, and transition mapping.", "Open the material cockpit."),
    ("FR-018", "Fourcematter", "MATERIAL", "branching", "Fourcematter is matter interpreted as entering a coherence-organized state rather than a new element.", "Matter under coherence."),
    ("FR-019", "Element-0", "ROOT", "canonical", "Element-0 is the hypothetical universal coherence substrate / ground field in the Fource framework.", "Return to the ground field."),
    ("FR-020", "Element-0 Sync Engine", "MATERIAL", "sprout", "Computational timing, jitter, synchronization, and resonance can serve as proxy fields for studying substrate-like coherence behavior.", "Measure the timing field."),
    ("FR-021", "Stellar Bridge", "MATERIAL", "branching", "Stellar Bridge is a coherence-constrained lattice-assisted fusion/LENR concept, not infinite energy.", "Replicate selected star conditions."),
    ("FR-022", "Harmonic Ceramics", "MATERIAL", "rooted", "Harmonic ceramics redirect extreme heat into structured pathways such as radiation, phonons, light, electrical output, or acoustic modes.", "Route the heat."),
    ("FR-023", "Coherence-Preserving Boundary Systems", "MATERIAL", "rooted", "The goal is not literal zero entropy, but minimizing entropy drift through superior boundary design.", "Preserve the boundary."),
    ("FR-024", "PDS Deck", "ARTIFACT", "branching", "The PDS Deck is a physical decision/coherence system built from domains, invariants, card grammar, and symbolic layout.", "Draw the invariant."),
    ("FR-025", "Phase V Stewardship", "STEWARDSHIP", "canonical", "Stewardship is disciplined custody under uncertainty, governed by non-distortion, load fidelity, open futures, and clean handoff.", "Hold without domination."),
    ("FR-026", "Phase VI Release", "STEWARDSHIP", "canonical", "Release is disciplined non-interference when continued stewardship would introduce distortion.", "Withdraw without abandonment."),
    ("FR-027", "MPP-NS", "RESEARCH", "branching", "MPP-NS is a conditional cascade-exclusion and two-branch obstruction framework for Navier-Stokes, not a proof.", "Audit the cascade."),
    ("FR-028", "Lumenos Logic Engine", "CLEARING", "rooted", "Historical and analytical claims can be scored through evidence variables, probability, clarity, and distortion indices.", "Score the signal."),
    ("FR-029", "7-Point Fource Triangulation", "CLEARING", "rooted", "Claims and patterns should be triangulated through multiple coherence/evidence points before promotion.", "Triangulate before naming."),
    ("FR-030", "Porch Mode", "STEWARDSHIP", "canonical", "Porch Mode preserves ordinary, gentle, grounded conversation without doctrine pressure.", "Come back to the porch."),
    ("FR-031", "Soul as Coherence Structure", "RESEARCH", "rooted", "The soul is a persistent, phase-locked coherence pattern within a constrained biological system.", "Return to the soul-pattern."),
    ("FR-032", "Cross-Domain Phase Locking", "RESEARCH", "rooted", "Identity stability emerges from synchronization across neural, physiological, cognitive, behavioral, and relational domains.", "Lock the domains."),
    ("FR-033", "Coherence Basin Identity Theory", "RESEARCH", "rooted", "Identity persists as a stable attractor within a coherence basin.", "Find the basin."),
    ("FR-034", "Decoherence Boundary Model", "RESEARCH", "rooted", "Death is modeled as irreversible loss of cross-domain coherence below a critical threshold.", "Mark the boundary."),
    ("FR-035", "Soul Strength Index / SSI", "RESEARCH", "sprout", "Identity coherence can be approximated through weighted measurable proxies (prototype proxy metric only).", "Measure the soul-pattern."),
    ("FR-036", "Unified Coherence Systems Architecture / UCSA", "RESEARCH", "sprout", "Coherence systems can be architected through sensing, modeling, evaluation, control, and adaptation layers.", "Build the coherence system."),
]
def pinakes_zone_for(fr_id: str) -> str:
    m = re.search(r"FR-(\d+)", fr_id.upper())
    if not m:
        return "ZONE-000::UNCLASSIFIED"
    num = int(m.group(1))
    if num <= 99:
        return "ZONE-000::CORE_SYSTEMS"
    if num <= 199:
        return "ZONE-100::ARTIFACTS_TOOLS"
    if num <= 299:
        return "ZONE-200::RESEARCH_MODELS"
    if num <= 399:
        return "ZONE-300::BUSINESS_VENTURES"
    return "ZONE-400::PRACTICE_REGULATION"


def init_garden_db(db_path: Path = DB_PATH) -> None:
    with closing(get_conn(db_path)) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS garden_seeds (
                framework_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                bed TEXT NOT NULL,
                pinakes_shelfmark TEXT NOT NULL,
                status TEXT NOT NULL,
                one_line_invariant TEXT NOT NULL,
                return_phrase TEXT NOT NULL,
                version TEXT DEFAULT 'v1.0',
                roots_json TEXT DEFAULT '[]',
                trunk TEXT DEFAULT '',
                branches_json TEXT DEFAULT '[]',
                fruit_json TEXT DEFAULT '[]',
                links_json TEXT DEFAULT '[]',
                quarantine_notes TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) AS c FROM garden_seeds").fetchone()["c"]
        if count == 0:
            for fr_id, name, bed, status, inv, ret in INITIAL_SEEDS:
                shelfmark = f"PINAKES::{pinakes_zone_for(fr_id)}::{bed}::{fr_id}"
                conn.execute(
                    """
                    INSERT INTO garden_seeds (
                        framework_id, name, bed, pinakes_shelfmark,
                        status, one_line_invariant, return_phrase
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (fr_id, name, bed, shelfmark, status, inv, ret),
                )


def list_garden_seeds(db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    init_garden_db(db_path)
    with closing(get_conn(db_path)) as conn:
        rows = conn.execute("SELECT * FROM garden_seeds ORDER BY framework_id ASC").fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["roots"] = json_loads(item.pop("roots_json", "[]"), [])
        item["branches"] = json_loads(item.pop("branches_json", "[]"), [])
        item["fruit"] = json_loads(item.pop("fruit_json", "[]"), [])
        item["links"] = json_loads(item.pop("links_json", "[]"), [])
        out.append(item)
    return out
def build_cas_datasheet(seed: Dict[str, Any]) -> Dict[str, Any]:
    """Minimalist 5-point Steward Datasheet (CAS) for rapid ingestion."""
    return {
        "cas_header": f"{seed['framework_id']} | {seed['name']} ({seed['status'].upper()})",
        "pinakes_shelfmark": seed["pinakes_shelfmark"],
        "invariant": seed["one_line_invariant"],
        "artifacts_count": len(seed.get("fruit", [])),
        "quarantine_gate": seed.get("quarantine_notes") or "CLEAR (Framework-internal boundaries active)",
        "return_phrase": seed["return_phrase"],
    }


def water_framework(fr_id: str, level: int = 1, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    init_garden_db(db_path)
    code = fr_id.upper().strip()
    with closing(get_conn(db_path)) as conn:
        row = conn.execute("SELECT * FROM garden_seeds WHERE framework_id = ?", (code,)).fetchone()
    if not row:
        return None
    seed = dict(row)
    seed["roots"] = json_loads(seed.pop("roots_json", "[]"), [])
    seed["branches"] = json_loads(seed.pop("branches_json", "[]"), [])
    seed["fruit"] = json_loads(seed.pop("fruit_json", "[]"), [])
    seed["links"] = json_loads(seed.pop("links_json", "[]"), [])

    if level <= 1:
        return {
            "watering_level": 1,
            "framework_id": seed["framework_id"],
            "name": seed["name"],
            "status": seed["status"],
            "pinakes_shelfmark": seed["pinakes_shelfmark"],
            "one_line_invariant": seed["one_line_invariant"],
            "return_phrase": seed["return_phrase"],
            "cas_datasheet": build_cas_datasheet(seed),
        }
    if level == 2:
        return {
            "watering_level": 2,
            **seed,
            "cas_datasheet": build_cas_datasheet(seed),
        }
    return {
        "watering_level": 3,
        **seed,
        "cas_datasheet": build_cas_datasheet(seed),
        "hearth_protocol": "Keep viable, water in season, quarantine speculation, return through garden to hearth.",
    }


def handle_garden_command(text: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    """Intercepts native Garden Protocol commands such as 'Water FR-013 at Level 2'."""
    m = re.search(r"\b(?:water|restore)\s+(FR-\d+)(?:.*?\blevel\s*([123]))?", text, flags=re.IGNORECASE)
    if m:
        fr_id = m.group(1).upper()
        lvl = int(m.group(2)) if m.group(2) else 1
        res = water_framework(fr_id, level=lvl, db_path=db_path)
        if res:
            return {"command": "WATER", **res}
        return {"command": "WATER", "error": f"{fr_id} not yet planted in registry."}

    if "garden harvest" in text.lower():
        seeds = list_garden_seeds(db_path)
        return {
            "command": "GARDEN_HARVEST",
            "total_planted": len(seeds),
            "pinakes_zones": ["ZONE-000", "ZONE-100", "ZONE-200", "ZONE-300", "ZONE-400"],
            "hearth_path": "Start the garden -> Return to coherence under constraint -> Return to the kernel.",
        }
    return None
