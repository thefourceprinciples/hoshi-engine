# Hoshi Engine (`v3.2.0`)

**Local-first cognitive archive, zero-speculation epistemic exocortex, and autonomous multi-pillar research engine built with Python 3, Flask, SQLite, and GitHub Actions.**

Hoshi functions as an air-gapped, cryptographically hashed knowledge vault (`O = 1.00`) that supplies verified primary texts, museum catalog leads, and geospatial dossiers to the **Lumen Observatory** front-end rather than allowing unverified web browsing or hallucinations.

---

### Core Architecture & 4-Tier Epistemic Pipeline

1. **Zero-Trust Institutional Whitelist (`hoshi/whitelist_compendium.json`):** Enforces a 7-pillar institutional allowlist covering ancient near-eastern and Mediterranean corpora, Asian and Islamic canons, indigenous archives, national libraries, public domain commons, and peer-reviewed indexes.
2. **Sanitized Multi-Pillar Harvester (`hoshi/harvester.py`):** Strips HTML/scripts, neutralizes prompt-injection directives inside quarantined sandboxes, computes a **SHA-256 cryptographic digest** (`O = 1.00`), and writes verified bundles to `canon/ANCHOR_<TARGET>.md`.
3. **Global Museum & Papyrological "Vault Hunter" (`hoshi/vault_hunter.py`):** Extracts attested lexical fingerprints and non-Latin script tokens, querying open catalogs (`OpenAlex`, `Internet Archive`) to generate `canon/VAULT_HUNT_<TARGET>.md` leads.
4. **Geospatial Provenance & Taphonomy Stratigraphy (`hoshi/stratigraphy.py`):** Maps historical acquisition trails, monastic scriptorium networks, and preservation filters into `canon/STRATIGRAPHY_<TARGET>.md`.
5. **Stateful Subspace Router & SQLite Memory Backbone (`hoshi/router.py`, `hoshi/db.py`, `hoshi/app.py`):** Local Flask & SQLite engine (`127.0.0.1:5001`) providing deterministic subspace routing and seed persistence.

---

### Repository Layout

```text
hoshi-engine/
├── .github/workflows/chronovisor_sleep.yml  # Scheduled 4-tier research pipeline
├── canon/                                   # SHA-256 verified dossiers
├── hoshi/                                   # Core package (app.py, db.py, harvester.py, router.py, etc.)
├── tests/test_hoshi.py                      # Automated pytest verification suite
├── app_identity.py                          # CLI and local web server entry point
├── RESEARCH_QUEUE.md                        # Dynamic autonomous research queue
└── requirements.txt
```

---

### Quickstart

* **Autonomous Cloud Research Mode:** Dispatch topics from the **Lumen Observatory** via `queue <topic>` or trigger the Chronovisor Sleep Cycle GitHub Action.
* **Local SQLite & Flask Server Mode:**
  ```bash
  pip install -r requirements.txt
  HOSHI_WEB=1 python app_identity.py   # Launches local REST API at http://127.0.0.1:5001
  python -m pytest -v                  # Runs automated verification suite
  ```

### License
AGPL-3.0 / MIT Dual-Track Open-Core Research Architecture — `thefourceprinciples`
