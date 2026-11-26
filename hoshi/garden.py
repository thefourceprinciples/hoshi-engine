from __future__ import annotations

import re
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, List, Optional

from .db import DB_PATH, get_conn, json_dumps, json_loads

VALID_STAGES = {
    "seed",
    "sprout",
    "rooted",
    "branching",
    "tree",
    "fruiting",
    "dormant",
    "composted",
    "quarantined",
    "market",
}


def almanac_zone_for(fr_id: str) -> str:
    m = re.search(r"FR-(\d+)", fr_id.upper())
    if not m:
        return "ZONE-000::UNCLASSIFIED"
    num = int(m.group(1))
    if num <= 99:
        return "ZONE-000::CORE_SYSTEMS"
    if num <= 199:
        return "ZONE-100::TOOLS_ARTIFACTS"
    if num <= 299:
        return "ZONE-200::RESEARCH_MODELS"
    if num <= 399:
        return "ZONE-300::MARKET_VENTURES"
    return "ZONE-400::PRACTICE_STEWARDSHIP"


def init_garden_db(db_path: Path = DB_PATH) -> None:
    with closing(get_conn(db_path)) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS garden_seeds (
                framework_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                bed TEXT NOT NULL,
                almanac_shelfmark TEXT NOT NULL,
                status TEXT NOT NULL,
                one_line_invariant TEXT NOT NULL,
                return_phrase TEXT NOT NULL,
                version TEXT DEFAULT 'v1.0',
                roots_json TEXT DEFAULT '[]',
                trunk TEXT DEFAULT '',
                branches_json TEXT DEFAULT '[]',
                fruit_json TEXT DEFAULT '[]',
                mycelium_json TEXT DEFAULT '[]',
                quarantine_notes TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def plant_seed(
    fr_id: str,
    name: str,
    invariant: str,
    bed: str = "CORE",
    status: str = "seed",
    return_phrase: str = "",
    quarantine_notes: str = "",
    db_path: Path = DB_PATH,
) -> Dict[str, Any]:
    init_garden_db(db_path)
    code = fr_id.upper().strip()
    clean_bed = bed.upper().strip() or "CORE"
    stage = status.lower().strip()
    if stage not in VALID_STAGES:
        stage = "seed"
    shelfmark = f"ALMANAC::{almanac_zone_for(code)}::{clean_bed}::{code}"
    ret = return_phrase.strip() or f"Return to {name.strip()}."

    with closing(get_conn(db_path)) as conn, conn:
        conn.execute(
            """
            INSERT INTO garden_seeds (
                framework_id, name, bed, almanac_shelfmark,
                status, one_line_invariant, return_phrase, quarantine_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(framework_id) DO UPDATE SET
                name = excluded.name,
                bed = excluded.bed,
                almanac_shelfmark = excluded.almanac_shelfmark,
                status = excluded.status,
                one_line_invariant = excluded.one_line_invariant,
                return_phrase = excluded.return_phrase,
                quarantine_notes = excluded.quarantine_notes,
                updated_at = CURRENT_TIMESTAMP
            """,
            (code, name.strip(), clean_bed, shelfmark, stage, invariant.strip(), ret, quarantine_notes.strip()),
        )
    return water_framework(code, level=1, db_path=db_path) or {}


def update_stage(fr_id: str, stage: str, note: str = "", db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    init_garden_db(db_path)
    code = fr_id.upper().strip()
    clean_stage = stage.lower().strip()
    if clean_stage not in VALID_STAGES:
        clean_stage = "rooted"
    with closing(get_conn(db_path)) as conn, conn:
        row = conn.execute("SELECT framework_id FROM garden_seeds WHERE framework_id = ?", (code,)).fetchone()
        if not row:
            return None
        if note.strip():
            conn.execute(
                "UPDATE garden_seeds SET status = ?, quarantine_notes = ?, updated_at = CURRENT_TIMESTAMP WHERE framework_id = ?",
                (clean_stage, note.strip(), code),
            )
        else:
            conn.execute(
                "UPDATE garden_seeds SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE framework_id = ?",
                (clean_stage, code),
            )
    return water_framework(code, level=1, db_path=db_path)


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
        item["mycelium"] = json_loads(item.pop("mycelium_json", "[]"), [])
        out.append(item)
    return out


def build_cas_field_card(seed: Dict[str, Any]) -> Dict[str, Any]:
    """Minimalist 5-line CAS Pocket Field Card for fast Steward ingestion."""
    return {
        "cas_id": f"{seed['framework_id']} | {seed['name']} [{seed['status'].upper()}]",
        "almanac_shelfmark": seed["almanac_shelfmark"],
        "invariant": seed["one_line_invariant"],
        "fruit_count": len(seed.get("fruit", [])),
        "gate_status": seed.get("quarantine_notes") or "CLEAR",
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
    seed["mycelium"] = json_loads(seed.pop("mycelium_json", "[]"), [])

    if level <= 1:
        return {
            "watering_level": 1,
            "framework_id": seed["framework_id"],
            "name": seed["name"],
            "status": seed["status"],
            "almanac_shelfmark": seed["almanac_shelfmark"],
            "one_line_invariant": seed["one_line_invariant"],
            "return_phrase": seed["return_phrase"],
            "cas_field_card": build_cas_field_card(seed),
        }
    return {
        "watering_level": min(3, max(2, level)),
        **seed,
        "cas_field_card": build_cas_field_card(seed),
    }


def handle_garden_command(text: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    """Handles Plant, Water/Restore, Compost, Quarantine, Market, and Garden Harvest commands."""
    clean = text.strip()

    plant_match = re.match(
        r"^plant\s+(FR-\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*(.+)$",
        clean,
        flags=re.IGNORECASE,
    )
    if plant_match:
        fr_id, name, bed, invariant = plant_match.groups()
        planted = plant_seed(fr_id, name, invariant, bed=bed, status="seed", db_path=db_path)
        return {"command": "PLANT", **planted}

    stage_match = re.match(
        r"^(compost|quarantine|market|promote)\s+(FR-\d+)(?:\s*\|\s*(.+))?$",
        clean,
        flags=re.IGNORECASE,
    )
    if stage_match:
        action, fr_id, note = stage_match.groups()
        stage_map = {
            "compost": "composted",
            "quarantine": "quarantined",
            "market": "market",
            "promote": "tree",
        }
        updated = update_stage(fr_id, stage_map[action.lower()], note=note or "", db_path=db_path)
        if updated:
            return {"command": action.upper(), **updated}
        return {"command": action.upper(), "error": f"{fr_id.upper()} not found in Farmer's Almanac."}

    water_match = re.search(r"\b(?:water|restore)\s+(FR-\d+)(?:.*?\blevel\s*([1-3]))?", clean, flags=re.IGNORECASE)
    if water_match:
        fr_id = water_match.group(1).upper()
        lvl = int(water_match.group(2)) if water_match.group(2) else 1
        res = water_framework(fr_id, level=lvl, db_path=db_path)
        if res:
            return {"command": "WATER", **res}
        return {"command": "WATER", "error": f"{fr_id} is not planted yet. Use: Plant {fr_id} | Name | Bed | Invariant"}

    if "garden harvest" in clean.lower():
        seeds = list_garden_seeds(db_path)
        return {
            "command": "GARDEN_HARVEST",
            "total_planted": len(seeds),
            "almanac_catalog": [build_cas_field_card(s) for s in seeds],
        }
    return None
