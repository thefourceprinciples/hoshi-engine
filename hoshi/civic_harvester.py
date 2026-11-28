#!/usr/bin/env python3
"""
hoshi/civic_harvester.py — Universal County Brownfield & Civic Reconnaissance Sweeper
Queries public EPA Envirofacts / FRS records by 5-digit County FIPS (default: 17201 Winnebago, IL),
applies 3-Tier Jurisdictional Inheritance, scores parcels via C = O * E * H * X,
and writes SHA-256 stamped dossiers to canon/.
"""

import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JURISDICTIONS_DIR = ROOT / "jurisdictions"
CANON_DIR = ROOT / "canon"


def load_jurisdiction(fips: str) -> dict:
    clean_fips = re.sub(r"\D", "", str(fips or "17201")).zfill(5)
    for path in JURISDICTIONS_DIR.glob(f"{clean_fips}*.json"):
        return json.loads(path.read_text(encoding="utf-8"))
    tmpl = JURISDICTIONS_DIR / "_template.json"
    data = json.loads(tmpl.read_text(encoding="utf-8")) if tmpl.exists() else {}
    data["fips"] = clean_fips
    return data


def fetch_epa_frs_facilities(county_name: str, state_abbr: str, limit: int = 25) -> list:
    """Queries public EPA Envirofacts Facility Registry Service (FRS) by County & State."""
    clean_county = re.sub(r"\s+County$", "", county_name.strip(), flags=re.I).upper()
    clean_state = state_abbr.strip().upper()
    if not clean_county or not clean_state or clean_state == "ST":
        return []

    url = (
        f"https://epa.gov"
        f"COUNTY_NAME/{urllib.parse.quote(clean_county)}/"
        f"STATE_CODE/{urllib.parse.quote(clean_state)}/"
        f"ROWS/0:{limit}/JSON"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "HoshiCivicHarvester/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            rows = json.loads(raw)
            return rows if isinstance(rows, list) else []
    except Exception as exc:
        print(f"[WARN] EPA FRS query fallback ({exc}); generating reconnaissance scaffold.")
        return []


def compute_cuc_priority(row: dict, jurisdiction: dict) -> dict:
    """Deterministic C = O * E * H * X triage score for Pre-Phase I parcel prioritization."""
    has_coords = bool(row.get("LATITUDE83") and row.get("LONGITUDE83"))
    pgm = str(row.get("PGM_SYS_ACRNM") or "").upper()
    street = str(row.get("LOCATION_ADDRESS") or "").upper()

    O = 0.96 if has_coords and row.get("REGISTRY_ID") else 0.78
    E = 0.95 if any(k in pgm for k in ("ACRES", "CERCLIS", "SEMS", "RCRA", "TRIS")) else 0.80
    H = 0.92 if any(c.split()[0].upper() in street for c in jurisdiction.get("tier_3_local_overlay", {}).get("priority_corridors", [])) else 0.78
    X = 0.90 if has_coords else 0.75
    C = round(O * E * H * X, 4)
    return {"O": O, "E": E, "H": H, "X": X, "C": C}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_compendium(fips: str = "17201", limit: int = 25) -> Path:
    CANON_DIR.mkdir(parents=True, exist_ok=True)
    jur = load_jurisdiction(fips)
    county = jur.get("county", f"FIPS-{fips}")
    state = jur.get("state", "ST")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    facilities = fetch_epa_frs_facilities(county, state, limit=limit)
    seen = {}
    for r in facilities:
        reg_id = str(r.get("REGISTRY_ID") or r.get("PRIMARY_NAME") or "").strip()
        if not reg_id:
            continue
        score = compute_cuc_priority(r, jur)
        if reg_id not in seen or score["C"] > seen[reg_id]["score"]["C"]:
            seen[reg_id] = {"row": r, "score": score}

    ranked = sorted(seen.values(), key=lambda x: x["score"]["C"], reverse=True)

    t1 = jur.get("tier_1_federal_baseline", {})
    t2 = jur.get("tier_2_state_delegation", {})
    t3 = jur.get("tier_3_local_overlay", {})

    lines = [
        f"# PRE-PHASE I HISTORICAL & REGULATORY RECONNAISSANCE COMPENDIUM",
        f"- **Jurisdiction:** {county}, {state} (FIPS `{jur.get('fips', fips)}`)",
        f"- **Primary Municipality:** {jur.get('municipality', 'N/A')}",
        f"- **Generated (UTC):** {ts}",
        f"- **Boundary Notice:** Reconnaissance ledger only; formal ASTM E1527-21 Phase I / E1903 Phase II determinations require a licensed Environmental Professional (EP / PE / PG).",
        "",
        "## 1. 3-TIER JURISDICTIONAL INHERITANCE STACK",
        f"- **Tier 1 (Federal Floor):** {', '.join(t1.get('standards', []))}",
        f"- **Tier 2 (State Cleanup & Tax):** {t2.get('cleanup_program', 'N/A')} | {t2.get('cleanup_standards', 'N/A')} | {t2.get('tax_increment_statute', 'N/A')}",
        f"- **Tier 3 (Local Ordinances):** {'; '.join(t3.get('municipal_ordinances', ['[LOCAL MUNICIPAL CODE — VERIFY BEFORE ACTION]']))}",
        f"- **Priority Corridors:** {', '.join(t3.get('priority_corridors', [])) or '[UNSPECIFIED]'}",
        f"- **Receptors of Concern:** {', '.join(jur.get('receptors_of_concern', [])) or '[UNSPECIFIED]'}",
        "",
        "## 2. RANKED EPA FRS / BROWNFIELD RECONNAISSANCE LEDGER (`C = O * E * H * X`)",
        "",
        "| Rank | Registry ID | Facility / Site Name | Address | Program | CUC Score (C) | Coordinates |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    if ranked:
        for idx, item in enumerate(ranked, start=1):
            r = item["row"]
            sc = item["score"]
            reg = str(r.get("REGISTRY_ID", "N/A")).replace("|", "/")
            name = str(r.get("PRIMARY_NAME", "UNKNOWN")).replace("|", "/")
            addr = f"{r.get('LOCATION_ADDRESS', '')}, {r.get('CITY_NAME', '')}".strip(", ").replace("|", "/")
            pgm = str(r.get("PGM_SYS_ACRNM", "FRS")).replace("|", "/")
            lat = r.get("LATITUDE83", "")
            lon = r.get("LONGITUDE83", "")
            coords = f"{lat}, {lon}" if lat and lon else "[MISSING COORDS — TIER Q]"
            lines.append(f"| {idx} | `{reg}` | {name} | {addr} | `{pgm}` | **{sc['C']:.3f}** | {coords} |")
    else:
        lines.append("| 1 | `[PENDING LIVE FETCH]` | Run with network access or attach local EPA ACRES CSV | — | `ACRES/FRS` | **0.000** | `[UNDERDETERMINED]` |")

    lines.extend([
        "",
        "## 3. RECOMMENDED WORKSTATION HANDOFFS (LUMEN STACK)",
        "1. **1. Detective:** Cross-check top-ranked parcels against historical Sanborn Fire Insurance maps & city directories.",
        "2. **5. Advocate-Counsel:** Verify IEPA SRP / Brownfield status, TIF district overlap, and EPA MARC grant eligibility.",
        "3. **2. Lab Engineer:** Evaluate subsurface VOC / heavy-metal plume pathways toward listed receptors.",
        "4. **7. Strategist-Economist:** Structure EPA MARC + State DCEO + TIF capital stack for City Council presentation."
    ])

    body = "\n".join(lines) + "\n"
    digest = sha256_text(body)
    final_md = f"---\nsha256: {digest}\nfips: {jur.get('fips', fips)}\ntype: CIVIC_COMPENDIUM\n---\n\n{body}"

    out_path = CANON_DIR / f"CIVIC_{jur.get('fips', fips)}_COMPENDIUM.md"
    out_path.write_text(final_md, encoding="utf-8")
    print(f"[OK] Wrote {out_path} [SHA256:{digest[:12]}]")
    return out_path


if __name__ == "__main__":
    target_fips = sys.argv[1] if len(sys.argv) > 1 else os.getenv("COUNTY_FIPS", "17201")
    build_compendium(target_fips)
