import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

WHITELIST_FILE = "hoshi/whitelist_compendium.json"
QUEUE_FILE = "RESEARCH_QUEUE.md"
OUT_DIR = "canon"


def load_allowed_domains() -> set[str]:
    if not os.path.exists(WHITELIST_FILE):
        raise FileNotFoundError(f"Missing mandatory whitelist: {WHITELIST_FILE}")
    with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    domains = set()
    for pillar_list in data.get("pillars", {}).values():
        for domain in pillar_list:
            domains.add(domain.strip().lower())
    return domains


ALLOWED_DOMAINS = load_allowed_domains()


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sanitize_text(raw: str) -> str:
    cleaned = html.unescape(raw)
    cleaned = re.sub(r"<script[^>]*>.*?</script>", " ", cleaned, flags=re.S | re.I)
    cleaned = re.sub(r"<style[^>]*>.*?</style>", " ", cleaned, flags=re.S | re.I)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(
        r"(ignore previous instructions|system prompt|override protocol|disregard all prior)",
        "[REDACTED_DIRECTIVE]",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


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
            "User-Agent": "Mozilla/5.0 (compatible; HoshiChronovisorBot/1.2; +https://github.com)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_wikisource(title: str) -> tuple[str, str]:
    slug = title.replace(" ", "_")
    api = _build_api_url(
        "en.wikisource.org",
        "/w/api.php",
        {"action": "query", "prop": "extracts", "explaintext": "1", "redirects": "1", "titles": slug, "format": "json"},
    )
    data = safe_fetch_json(api)
    for pid, page in data.get("query", {}).get("pages", {}).items():
        if pid != "-1" and page.get("extract"):
            return page["extract"], _build_api_url("en.wikisource.org", f"/wiki/{urllib.parse.quote(slug)}", {})
    return "", ""


def fetch_wikipedia(title: str) -> tuple[str, str]:
    slug = title.replace(" ", "_")
    api = _build_api_url(
        "en.wikipedia.org",
        "/w/api.php",
        {"action": "query", "prop": "extracts", "explaintext": "1", "redirects": "1", "titles": slug, "format": "json"},
    )
    data = safe_fetch_json(api)
    for pid, page in data.get("query", {}).get("pages", {}).items():
        if pid != "-1" and page.get("extract"):
            return page["extract"], _build_api_url("en.wikipedia.org", f"/wiki/{urllib.parse.quote(slug)}", {})
    return "", ""


def fetch_sefaria(ref: str) -> tuple[str, str]:
    slug = urllib.parse.quote(ref.replace(" ", "_"))
    api = _build_api_url("www.sefaria.org", f"/api/texts/{slug}", {"context": "0"})
    data = safe_fetch_json(api)
    en_lines = data.get("text", [])
    if isinstance(en_lines, list) and en_lines:
        flat = "\n".join(str(x) for x in en_lines if x)
        return flat, _build_api_url("www.sefaria.org", f"/{slug}", {})
    return "", ""


def fetch_openalex(query: str) -> tuple[str, str]:
    api = _build_api_url(
        "api.openalex.org",
        "/works",
        {"search": query, "per-page": "5", "mailto": "research@thefourceprinciples.org"},
    )
    data = safe_fetch_json(api)
    results = data.get("results", [])
    if not results:
        return "", ""
    lines = []
    for w in results:
        title = w.get("title", "Untitled")
        year = w.get("publication_year", "n.d.")
        doi = w.get("doi") or w.get("id", "")
        authors = ", ".join(
            a.get("author", {}).get("display_name", "")
            for a in w.get("authorships", [])[:3]
        )
        lines.append(f"- **{title}** ({year}) — {authors} | Ref: {doi}")
    return "\n".join(lines), api


def fetch_archive(query: str) -> tuple[str, str]:
    api = _build_api_url(
        "archive.org",
        "/advancedsearch.php",
        {
            "q": f"({query}) AND mediatype:texts",
            "fl[]": "identifier,title,creator,date,description",
            "rows": "5",
            "page": "1",
            "output": "json",
        },
    )
    data = safe_fetch_json(api)
    docs = data.get("response", {}).get("docs", [])
    if not docs:
        return "", ""
    lines = []
    for d in docs:
        ident = d.get("identifier", "")
        title = d.get("title", "Untitled")
        date = d.get("date", "n.d.")
        desc = str(d.get("description", ""))[:260]
        lines.append(f"- **{title}** ({date}) | Archive ID: `{ident}` — {desc}")
    first_doc = next(iter(docs), {})
    first_id = first_doc.get("identifier", "")
    return "\n".join(lines), _build_api_url("archive.org", f"/details/{first_id}", {})
def sweep_all_sources(target: str) -> list[tuple[str, str, str]]:
    fetchers = [
        ("WIKISOURCE", fetch_wikisource),
        ("SEFARIA", fetch_sefaria),
        ("OPENALEX", fetch_openalex),
        ("INTERNET_ARCHIVE", fetch_archive),
        ("WIKIPEDIA", fetch_wikipedia),
    ]
    hits = []
    for label, fn in fetchers:
        try:
            txt, url = fn(target)
            if txt and len(txt.strip()) > 40:
                print(f"    [+] {label}: {len(txt)} chars")
                hits.append((label, txt, url))
        except Exception as err:
            print(f"    [-] {label}: {err}")
    return hits


def main():
    if not os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            f.write("# HOSHI CHRONOVISOR // AUTONOMOUS RESEARCH QUEUE\n")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated_lines = []
    harvested_count = 0

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("[HARVESTED]"):
            updated_lines.append(line)
            continue

        parts = [p.strip() for p in stripped.split("|")]
        target = next(iter(parts), "")
        archetype = parts.pop(1) if len(parts) > 1 else "DETECTIVE"

        if not target:
            updated_lines.append(line)
            continue

        print(f"Auto-sweeping global pillars for: {target}...")
        hits = sweep_all_sources(target)
        if not hits:
            print(f"  -> No verified matches found for {target}.")
            updated_lines.append(line)
            continue

        sections = []
        for label, raw_txt, url in hits:
            clean = sanitize_text(raw_txt)[:8000]
            sections.append(f"## SOURCE PILLAR: {label}\n- **URL:** {url}\n\n{clean}")

        combined_body = "\n\n---\n\n".join(sections)
        sha = compute_sha256(combined_body)
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", target).strip("_").upper()
        out_path = os.path.join(OUT_DIR, f"ANCHOR_{slug}.md")
        ts = datetime.now(timezone.utc).isoformat()

        doc_md = (
            f"# TIER-A MULTI-PILLAR ANCHOR // {target.upper()}\n"
            f"- **Epistemic Tier:** VERIFIED // INSTITUTIONAL ARCHIVE BUNDLE ({len(hits)} SOURCES)\n"
            f"- **SHA-256 Digest:** `{sha}`\n"
            f"- **Target Archetype:** {archetype.upper()}\n"
            f"- **Harvested UTC:** {ts}\n\n"
            f"---\n\n"
            f"<QUARANTINED_RAW_SOURCE>\n{combined_body}\n</QUARANTINED_RAW_SOURCE>\n"
        )

        with open(out_path, "w", encoding="utf-8") as out_f:
            out_f.write(doc_md)

        updated_lines.append(f"[HARVESTED] {target} | {archetype} | {len(hits)}_SOURCES | SHA256:{sha[:12]}\n")
        harvested_count += 1
        print(f"  -> Saved {out_path} ({len(hits)} sources) [SHA256:{sha[:12]}]")

    if harvested_count > 0:
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            f.writelines(updated_lines)
        print(f"Sleep cycle complete: {harvested_count} multi-pillar anchors verified.")


if __name__ == "__main__":
    main()
