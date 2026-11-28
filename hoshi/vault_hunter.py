import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone

WHITELIST_FILE = "hoshi/whitelist_compendium.json"
CANON_DIR = "canon"

STOPWORDS = {
    "about", "after", "again", "against", "all", "also", "and", "another",
    "any", "are", "because", "been", "before", "being", "between", "both",
    "but", "can", "could", "did", "does", "doing", "down", "during", "each",
    "few", "for", "from", "further", "had", "has", "have", "having", "her",
    "here", "hers", "herself", "him", "himself", "his", "how", "into", "its",
    "itself", "just", "more", "most", "myself", "nor", "not", "now", "off",
    "once", "only", "other", "our", "ours", "out", "over", "own", "same",
    "she", "should", "some", "such", "than", "that", "the", "their", "theirs",
    "them", "themselves", "then", "there", "these", "they", "this", "those",
    "through", "under", "until", "very", "was", "were", "what", "when",
    "where", "which", "while", "who", "whom", "why", "will", "with", "would",
    "your", "yours", "source", "pillar", "https", "http", "wiki", "org",
    "com", "www", "url", "tier", "anchor", "verified", "harvested", "utc",
}

MUSEUM_COLLECTIONS = [
    ("Berlin Papyrus Collection (Ägyptisches Museum / SMB)", "berliner-papyrusdatenbank.smb.museum", "Coptic & Greek codices (BG 8502, Akhmim/Panopolis provenance, Carl Reinhardt 1896 batch)"),
    ("Egypt Exploration Society / Oxyrhynchus Collection (Oxford)", "www.ees.ac.uk", "Uncataloged Grenfell & Hunt boxes, 2nd–4th c. CE literary & apocryphal Greek fragments"),
    ("John Rylands Research Institute & Library (Manchester)", "www.digitalcollections.manchester.ac.uk", "P.Ryl. Greek & Coptic papyri, Rendel Harris / Grenfell acquisitions"),
    ("Austrian National Library — Papyrussammlung (Vienna)", "papyri.info", "Archduke Rainer Faiyum & Hermopolis cartonnage/codex fragments"),
    ("Leon Levy Dead Sea Scrolls Digital Library (IAA)", "www.deadseascrolls.org.il", "Unidentified Qumran Cave 4 & Judean Desert leather/papyrus scraps"),
]


def load_allowed_domains() -> set[str]:
    if not os.path.exists(WHITELIST_FILE):
        return {"api.openalex.org", "archive.org"}
    with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    domains = set()
    for pillar_list in data.get("pillars", {}).values():
        for domain in pillar_list:
            domains.add(domain.strip().lower())
    return domains


ALLOWED_DOMAINS = load_allowed_domains()


def safe_fetch_json(url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    if host not in ALLOWED_DOMAINS:
        raise ValueError(f"SECURITY BLOCK — Non-whitelisted domain: {host}")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "HoshiVaultHunter/1.0 (https://github.com)"},
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_lexical_fingerprint(text: str) -> dict:
    body_match = re.search(r"<QUARANTINED_RAW_SOURCE>(.*?)</QUARANTINED_RAW_SOURCE>", text, flags=re.S)
    clean_body = body_match.group(1) if body_match else text
    clean_body = re.sub(r"https?://\S+", " ", clean_body)

    words = re.findall(r"\b[A-Za-z]{4,}\b", clean_body.lower())
    filtered = [w for w in words if w not in STOPWORDS]
    top_terms = [w for w, _ in Counter(filtered).most_common(12)]

    proper_nouns = re.findall(r"\b[A-Z][a-z]{3,}(?:\s+[A-Z][a-z]{3,})?\b", clean_body)
    proper_filtered = [
        p for p in proper_nouns
        if p.lower() not in STOPWORDS and not p.startswith(("Source", "Tier", "Archive", "Pillar"))
    ]
    top_entities = [p for p, _ in Counter(proper_filtered).most_common(10)]

    non_latin = re.findall(r"[\u0370-\u03FF\u2C80-\u2CFF\u0590-\u05FF]{3,}", clean_body)
    top_scripts = [s for s, _ in Counter(non_latin).most_common(8)]

    return {
        "top_terms": top_terms,
        "top_entities": top_entities,
        "top_scripts": top_scripts,
    }
def query_archival_leads(target_title: str) -> list[str]:
    leads = []
    q_paper = urllib.parse.quote(f"{target_title} manuscript papyrus fragment provenance")
    try:
        oa_url = f"https://openalex.org{q_paper}&per-page=5"
        oa_data = safe_fetch_json(oa_url)
        for w in oa_data.get("results", []):
            title = w.get("title", "Untitled")
            year = w.get("publication_year", "n.d.")
            doi = w.get("doi") or w.get("id", "")
            leads.append(f"- **[OPENALEX PAPYROLOGY]** {title} ({year}) — `{doi}`")
    except Exception:
        pass

    q_cat = urllib.parse.quote(f"({target_title}) AND (papyrus OR codex OR fragment OR cartonnage) AND mediatype:texts")
    try:
        ia_url = f"https://archive.org{q_cat}&fl[]=identifier,title,date&rows=5&page=1&output=json"
        ia_data = safe_fetch_json(ia_url)
        for d in ia_data.get("response", {}).get("docs", []):
            ident = d.get("identifier", "")
            title = d.get("title", "Untitled")
            date = d.get("date", "n.d.")
            leads.append(f"- **[ARCHIVE CATALOG]** {title} ({date}) — `https://archive.org{ident}`")
    except Exception:
        pass

    return leads


def run_vault_hunt():
    if not os.path.exists(CANON_DIR):
        print("No canon/ directory found.")
        return

    anchor_files = [
        f for f in os.listdir(CANON_DIR)
        if f.startswith("ANCHOR_") and f.endswith(".md")
    ]
    generated = 0

    for fname in sorted(anchor_files):
        anchor_path = os.path.join(CANON_DIR, fname)
        hunt_name = fname.replace("ANCHOR_", "VAULT_HUNT_", 1)
        hunt_path = os.path.join(CANON_DIR, hunt_name)

        if os.path.exists(hunt_path):
            continue

        with open(anchor_path, "r", encoding="utf-8") as f:
            raw_anchor = f.read()

        target_label = fname.replace("ANCHOR_", "").replace(".md", "").replace("_", " ")
        print(f"Vault Hunter scanning archival leads for: {target_label}...")

        fp = extract_lexical_fingerprint(raw_anchor)
        leads = query_archival_leads(target_label)

        terms_str = ", ".join(f"`{t}`" for t in fp.get("top_terms", [])) or "`[NONE EXTRACTED]`"
        entities_str = ", ".join(f"`{e}`" for e in fp.get("top_entities", [])) or "`[NONE EXTRACTED]`"
        scripts_str = ", ".join(f"`{s}`" for s in fp.get("top_scripts", [])) or "`[LATIN TRANSLITERATION ONLY IN ANCHOR]`"
        leads_block = "\n".join(leads) if leads else "- `[NO DIRECT CATALOG HITS RETURNED — MANUAL CURATOR QUERY REQUIRED]`"

        museums_block = "\n".join(
            f"- **{name}** (`{dom}`): {note}" for name, dom, note in MUSEUM_COLLECTIONS
        )

        body = (
            f"## 1. VERIFIED LEXICAL & SCRIBAL FINGERPRINT (DERIVED FROM {fname})\n"
            f"- **High-Signal Terms:** {terms_str}\n"
            f"- **Attested Proper Entities:** {entities_str}\n"
            f"- **Original Script Tokens (Greek/Coptic/Hebrew):** {scripts_str}\n\n"
            f"## 2. SCHOLARLY & ARCHIVAL CATALOG LEADS\n"
            f"{leads_block}\n\n"
            f"## 3. PRIORITY MUSEUM & PAPYROLOGICAL VAULT TARGETS\n"
            f"{museums_block}\n\n"
            f"## 4. ANTI-PAREIDOLIA EPISTEMIC NOTICE\n"
            f"- Any unrecovered folios or missing leaves remain strictly **`[MISSING WITNESS — UNDERDETERMINED]`** (Tier Q) until physically matched against museum inventory numbers.\n"
        )

        sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
        ts = datetime.now(timezone.utc).isoformat()
        header = (
            f"# TIER-3 VAULT HUNTER DOSSIER // {target_label}\n"
            f"- **Parent Anchor:** `{fname}`\n"
            f"- **SHA-256 Digest:** `{sha}`\n"
            f"- **Generated UTC:** {ts}\n\n---\n\n"
        )

        with open(hunt_path, "w", encoding="utf-8") as out_f:
            out_f.write(header + body)

        generated += 1
        print(f"  -> Generated {hunt_path} [SHA256:{sha[:12]}]")

    print(f"Vault Hunter sweep complete: {generated} new archival dossiers created.")


if __name__ == "__main__":
    run_vault_hunt()
