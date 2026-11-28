import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

WHITELIST_FILE = "hoshi/whitelist_compendium.json"
CANON_DIR = "canon"

STRATIGRAPHY_CORRIDORS = [
    {
        "id": "UPPER_EGYPT_PANOPOLIS",
        "keywords": ["mary", "berlin", "8502", "akhmim", "panopolis", "shenoute", "coptic", "sahidic"],
        "region": "Panopolis / Akhmim & Sohag Escarpment (Upper Egypt)",
        "provenance_chain": "Carl Reinhardt 1896 Cairo antiquity purchase -> traced to Akhmim (ancient Panopolis) burial/monastic provenance.",
        "monastic_network": "White Monastery (Deir el-Anba Shenouda) & Red Monastery (Deir el-Anba Bishay) scriptorium corridor; Pachomian federation south toward Nag Hammadi.",
        "taphonomy_filter": "Arid eastern/western desert limestone cliff escarpments and elevated cemetery tells strictly above the historical Nile alluvial floodline (9th Panopolite Nome).",
        "survey_query": "Akhmim Panopolis monastery archaeology survey papyrus excavation",
    },
    {
        "id": "UPPER_EGYPT_NAG_HAMMADI",
        "keywords": ["nag hammadi", "apocryphon", "thomas", "chenoboskion", "pachomius", "jabal"],
        "region": "Jabal al-Tarif / Chenoboskion & Faw Qibli (Upper Egypt)",
        "provenance_chain": "December 1945 discovery by Muhammad Ali al-Samman at the base of Jabal al-Tarif cliff near Hamra Dom.",
        "monastic_network": "Pachomian motherhouse at Pbow (Faw Qibli) and Chenoboskion (al-Qasr) within 5–10 km of the cliff talus.",
        "taphonomy_filter": "Sub-escarpment limestone talus caves and dry desert rock-cut tombs above the Qena Bend Nile floodplain.",
        "survey_query": "Jabal al-Tarif Nag Hammadi Pachomian archaeology survey",
    },
    {
        "id": "MIDDLE_EGYPT_OXYRHYNCHUS",
        "keywords": ["oxyrhynchus", "3525", "rylands", "463", "bahnasa", "grenfell", "hunt", "faiyum"],
        "region": "Oxyrhynchus (El-Bahnasa) & Faiyum Basin (Middle Egypt)",
        "provenance_chain": "Grenfell & Hunt (1896–1907) Egypt Exploration Fund excavations of ancient urban kôm mounds; Rylands acquisitions via Rendel Harris.",
        "monastic_network": "4th–5th c. CE Oxyrhynchite monastic churches and scriptoria documented in Rufinus' Historia Monachorum.",
        "taphonomy_filter": "High wind-blown sand-covered rubbish mounds (kôms) along the Bahr Yussef western desert margin above irrigation seepage.",
        "survey_query": "Oxyrhynchus El-Bahnasa papyri archaeological survey kôm",
    },
    {
        "id": "JUDEAN_DESERT_QUMRAN",
        "keywords": ["dead sea", "qumran", "enoch", "murabba", "judean", "essene", "scroll"],
        "region": "Northwestern Dead Sea Escarpment & Judean Desert Wadis",
        "provenance_chain": "1946–1956 Bedouin and IAA/École Biblique recoveries across Qumran Caves 1–11, Wadi Murabba'at, and Nahal Hever.",
        "monastic_network": "Khirbet Qumran communal settlement and Second Temple scribal workshops.",
        "taphonomy_filter": "Hyper-arid marl terrace caves and upper limestone cliff fissures in the Jordan Rift rain-shadow well above Dead Sea shoreline fluctuations.",
        "survey_query": "Qumran Judean Desert caves archaeological survey remote sensing",
    },
]


def load_allowed_domains() -> set[str]:
    if not os.path.exists(WHITELIST_FILE):
        return {"api.openalex.org"}
    with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    domains = set()
    for pillar_list in data.get("pillars", {}).values():
        for domain in pillar_list:
            domains.add(domain.strip().lower())
    return domains


ALLOWED_DOMAINS = load_allowed_domains()


def _build_api_url(host: str, path: str, params: dict) -> str:
    query_str = urllib.parse.urlencode(params)
    return urllib.parse.urlunparse(("https", host, path, "", query_str, ""))


def safe_fetch_json(url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    if host not in ALLOWED_DOMAINS:
        raise ValueError(f"SECURITY BLOCK — Non-whitelisted domain: {host}")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; HoshiStratigraphyEngine/1.0; +https://github.com/thefourceprinciples/hoshi-engine)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))
def match_corridors(text_lower: str) -> list[dict]:
    matched = []
    for c in STRATIGRAPHY_CORRIDORS:
        hits = sum(1 for kw in c.get("keywords", []) if kw in text_lower)
        if hits > 0:
            matched.append((hits, c))
    matched.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in matched]


def fetch_survey_literature(query: str) -> list[str]:
    papers = []
    try:
        oa_url = _build_api_url(
            "api.openalex.org",
            "/works",
            {
                "search": query,
                "per-page": "4",
                "mailto": "research@thefourceprinciples.org",
            },
        )
        data = safe_fetch_json(oa_url)
        for w in data.get("results", []):
            title = w.get("title", "Untitled")
            year = w.get("publication_year", "n.d.")
            doi = w.get("doi") or w.get("id", "")
            papers.append(f"- **[EXCAVATION / SURVEY PAPER]** {title} ({year}) — `{doi}`")
    except Exception as err:
        print(f"    [-] OpenAlex Survey query: {err}")
    return papers


def run_stratigraphy():
    if not os.path.exists(CANON_DIR):
        print("No canon/ directory found.")
        return

    anchor_files = [
        f for f in os.listdir(CANON_DIR)
        if f.startswith("ANCHOR_") and f.endswith(".md")
    ]
    created = 0

    for fname in sorted(anchor_files):
        anchor_path = os.path.join(CANON_DIR, fname)
        strat_name = fname.replace("ANCHOR_", "STRATIGRAPHY_", 1)
        strat_path = os.path.join(CANON_DIR, strat_name)

        if os.path.exists(strat_path):
            continue

        with open(anchor_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        target_label = fname.replace("ANCHOR_", "").replace(".md", "").replace("_", " ")
        print(f"Stratigraphy modeling geospatial corridors for: {target_label}...")

        corridors = match_corridors((target_label + " " + raw_text[:4000]).lower())
        if not corridors:
            corridor_sections = (
                "## 1. CORRIDOR STATUS\n"
                "- **`[PROVENANCE CORRIDOR — UNDERDETERMINED]`**: No pre-mapped Mediterranean/ANE corridor matched this anchor automatically. Manual historical gazetteer coordinates required.\n"
            )
        else:
            blocks = []
            for idx, c in enumerate(corridors[:2], start=1):
                papers = fetch_survey_literature(c["survey_query"])
                papers_md = "\n".join(papers) if papers else "- `[NO RECENT OPENALEX SURVEY PAPERS RETURNED]`"
                blocks.append(
                    f"## {idx}. CANDIDATE ZONE // {c['region']}\n"
                    f"- **Verified Provenance Trail:** {c['provenance_chain']}\n"
                    f"- **Monastic & Scriptorium Network:** {c['monastic_network']}\n"
                    f"- **Hydrological & Taphonomic Filter:** {c['taphonomy_filter']}\n"
                    f"- **Peer-Reviewed Survey Literature:**\n{papers_md}\n"
                )
            corridor_sections = "\n---\n\n".join(blocks)

        epistemic_gate = (
            "\n---\n\n## EPISTEMIC & FIELD SURVEY GATE (TIER-1 LOCK)\n"
            "- Geospatial zones above represent **falsifiable archival and archaeological hypotheses** derived from verified provenance and preservation physics—not confirmed excavation finds.\n"
        )

        body = corridor_sections + epistemic_gate
        sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
        ts = datetime.now(timezone.utc).isoformat()
        header = (
            f"# TIER-4 GEOSPATIAL STRATIGRAPHY & SITE MODEL // {target_label}\n"
            f"- **Parent Anchor:** `{fname}`\n"
            f"- **UCMS Layer:** Layer 1 (Physical / Geospatial / Taphonomic Substrate)\n"
            f"- **SHA-256 Digest:** `{sha}`\n"
            f"- **Generated UTC:** {ts}\n\n---\n\n"
        )

        with open(strat_path, "w", encoding="utf-8") as out_f:
            out_f.write(header + body)

        created += 1
        print(f"  -> Generated {strat_path} [SHA256:{sha[:12]}]")

    print(f"Stratigraphy pass complete: {created} geospatial dossiers created.")


if __name__ == "__main__":
    run_stratigraphy()
