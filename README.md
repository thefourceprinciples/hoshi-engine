# Hoshi Engine (`v3.1.0`)

**Local-first stateful cognitive archive, subspace router, and SQLite memory backbone built with Python 3 and Flask.**

Instead of treating every prompt as a stateless `input -> output` exchange, Hoshi routes signals through a deterministic state machine that preserves identity continuity, memory provenance, and contamination guardrails across sessions:

```text
input -> signal parser -> subspace router -> SQLite memory / identity / timeline -> output
```

---

### Modular Architecture

```text
hoshi-engine/
├── hoshi/
│   ├── __init__.py     # Package version & metadata
│   ├── db.py           # SQLite schema initialization & persistence helpers
│   ├── parser.py       # Intent, role, capsule, ambiguity & contamination parsing
│   ├── router.py       # Coherence scoring, subspace transitions, Chronovisor & manifest ingestion
│   └── app.py          # Flask dashboard, CORS-enabled JSON API & health routes
├── tests/
│   └── test_hoshi.py   # Automated pytest verification suite
├── app_identity.py     # CLI and local web server entry point
└── requirements.txt
```

---

### Core Capabilities

* **Stateful Subspace Routing:** Transitions smoothly across `REFLECTIVE`, `BRIDGE`, `EXECUTION`, `ARCHIVE`, `IDENTITY`, and `CHRONOVISOR` states based on signal intent, action pressure, and ambiguity.
* **Contamination & Recovery Guardrails:** Detects malformed payloads, SQL injection patterns, and high-entropy blobs—automatically blocking unsafe transitions and locking into `recovery` mode.
* **Structured Manifest Ingestion:** Parses `HOSHI_MANIFEST_START ... HOSHI_MANIFEST_END` blocks to bulk-insert deduplicated memories, anchor weights, and active capsules.
* **Chronovisor Timeline Reconstruction:** Extracts temporal anchors (`YYYY`) and named entities to assemble provisional sequence hypotheses.
* **CORS-Enabled Local REST API:** Exposes `/api/respond`, `/api/state`, `/api/timeline`, `/api/memory`, and `/health` on `127.0.0.1:5001` so browser front-ends (such as `Lumen`) can archive state directly into local SQLite.

---

### Quickstart

#### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Run Interactive CLI Mode
```bash
python app_identity.py
```

#### 3. Launch Web Dashboard & Local JSON API (`http://127.0.0.1:5001`)
```bash
HOSHI_WEB=1 python app_identity.py
```

#### 4. Run Automated Tests
```bash
python -m pytest -v
```

---

### License
MIT License
