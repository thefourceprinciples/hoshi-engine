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


def safe_fetch_json(url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    if host not in ALLOWED_DOMAINS:
        raise ValueError(f"SECURITY BLOCK — Non-whitelisted domain: {host}")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "HoshiChronovisorHarvester/1.0 (https://github.com)"
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_wikisource(title: str) -> tuple[str, str]:
    slug = urllib.parse.quote(title.replace(" ", "_"))
    api = f"https://wikisource.org{slug}&format=json"
    data = safe_fetch_json(api)
    pages = data.get("query", {}).get("pages", {})
    for pid, page in pages.items():
        if pid != "-1" and page.get("extract"):
            return page["extract"], f"https://wikisource.org{slug}"
    return "", ""


def fetch_wikipedia(title: str) -> tuple[str, str]:
    slug = urllib.parse.quote(title.replace(" ", "_"))
    api = f"https://wikipedia.org{slug}&format=json"
    data = safe_fetch_json(api)
    pages = data.get("query", {}).get("pages", {})
    for pid, page in pages.items():
        if pid != "-1" and page.get("extract"):
            return page["extract"], f"https://wikipedia.org{slug}"
    return "", ""


def fetch_sefaria(ref: str) -> tuple[str, str]:
    slug = urllib.parse.quote(ref.replace(" ", "_"))
    api = f"https://sefaria.org{slug}?context=0"
    data = safe_fetch_json(api)
    en_lines = data.get("text", [])
    if isinstance(en_lines, list) and en_lines:
        flat = "\n".join(str(x) for x in en_lines if x)
        return flat, f"https://sefaria.org{slug}"
    return "", ""


def fetch_openalex(query: str) -> tuple[str, str]:
    q = urllib.parse.quote(query)
    api = f"https://openalex.org{q}&per-page=5"
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
    return "\n".join(lines), f"https://openalex.org{q}"


def fetch_archive(query: str) -> tuple[str, str]:
    q = urllib.parse.quote(f"({query}) AND mediatype:texts")
    api = f"https://archive.org{q}&fl[]=identifier,title,creator,date,description&rows=5&page=1&output=json"
    data = safe_fetch_json(api)
    docs = data.get("response", {}).get("docs", [])
    if not docs:
        return "", ""
    lines = []
    for d in docs:
        ident = d.get("identifier", "")
        title = d.get("title", "Untitled")
        date = d.get("date", "n.d.")
        desc = str(d.get("description", ""))[:300]
        lines.append(f"- **{title}** ({date}) | Archive ID: `{ident}` — {desc}")
    return "\n".join(lines), f"https://archive.org{docs.get('identifier', '')}"


def harvest_target(target: str, hint: str) -> tuple[str, str]:
    hint = hint.lower().strip()
    if hint == "sefaria":
        return fetch_sefaria(target)
    if hint == "openalex":
        return fetch_openalex(target)
    if hint == "archive":
        return fetch_archive(target)
    if hint == "wikisource":
        txt, src = fetch_wikisource(target)
        if txt:
            return txt, src
    return fetch_wikipedia(target)


def main():
    if not os.path.exists(QUEUE_FILE):
        print("No RESEARCH_QUEUE.md found.")
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
        target = parts
        archetype = parts if len(parts) > 1 else "detective"
        hint = parts if len(parts) > 2 else "wikisource"

        print(f"Harvesting: {target} (source={hint}, whitelist={len(ALLOWED_DOMAINS)} domains)...")
        try:
            raw_text, source_url = harvest_target(target, hint)
            if not raw_text:
                print(f"  -> No verified text returned for {target}.")
                updated_lines.append(line)
                continue

            clean_text = sanitize_text(raw_text)[:20000]
            sha = compute_sha256(clean_text)
            slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", f"{target}_{hint}").strip("_").upper()
            out_path = os.path.join(OUT_DIR, f"ANCHOR_{slug}.md")
            ts = datetime.now(timezone.utc).isoformat()

            doc_md = (
                f"# TIER-A VERIFIED ANCHOR // {target.upper()}\n"
                f"- **Epistemic Tier:** VERIFIED // INSTITUTIONAL ARCHIVE ({hint.upper()})\n"
                f"- **SHA-256 Digest:** `{sha}`\n"
                f"- **Source URL:** {source_url}\n"
                f"- **Target Archetype:** {archetype.upper()}\n"
                f"- **Harvested UTC:** {ts}\n\n"
                f"---\n\n"
                f"<QUARANTINED_RAW_SOURCE>\n{clean_text}\n</QUARANTINED_RAW_SOURCE>\n"
            )

            with open(out_path, "w", encoding="utf-8") as out_f:
                out_f.write(doc_md)

            updated_lines.append(f"[HARVESTED] {stripped} | SHA256:{sha[:12]}\n")
            harvested_count += 1
            print(f"  -> Saved {out_path} [SHA256:{sha[:12]}]")
        except Exception as exc:
            print(f"  -> Error harvesting {target}: {exc}")
            updated_lines.append(line)

    if harvested_count > 0:
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            f.writelines(updated_lines)
        print(f"Sleep cycle complete: {harvested_count} anchors verified and hashed.")


if __name__ == "__main__":
    main()
