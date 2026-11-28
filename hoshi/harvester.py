{
  "version": "1.1.0",
  "policy": "STRICT_INSTITUTIONAL_ALLOWLIST",
  "pillars": {
    "ancient_mediterranean_ane": [
      "www.sefaria.org",
      "papyri.info",
      "www.trismegistos.org",
      "www.perseus.tufts.edu",
      "cdli.mpiwg-berlin.mpg.de",
      "etcsl.orinst.ox.ac.uk",
      "berliner-papyrusdatenbank.smb.museum",
      "www.ees.ac.uk",
      "www.digitalcollections.manchester.ac.uk",
      "www.deadseascrolls.org.il"
    ],
    "asian_south_asian_islamic": [
      "ctext.org",
      "suttacentral.net",
      "gretil.sub.uni-goettingen.de"
    ],
    "americas_africa_endangered": [
      "www.famsi.org",
      "www.loc.gov",
      "eap.bl.uk"
    ],
    "european_national_libraries": [
      "gallica.bnf.fr",
      "digital.bodleian.ox.ac.uk",
      "digi.vatlib.it",
      "www.dmgh.de",
      "www.europeana.eu"
    ],
    "national_archives": [
      "catalog.archives.gov",
      "discovery.nationalarchives.gov.uk",
      "whc.unesco.org"
    ],
    "primary_text_commons": [
      "en.wikisource.org",
      "archive.org",
      "www.gutenberg.org",
      "en.wikipedia.org"
    ],
    "scholarly_science_indexes": [
      "api.openalex.org",
      "api.crossref.org",
      "eutils.ncbi.nlm.nih.gov",
      "zenodo.org"
    ]
  }
}
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
                hits.append((label, txt, url))
        except Exception:
            continue
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
        target = parts[0]
        archetype = parts[1] if len(parts) > 1 else "DETECTIVE"

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
