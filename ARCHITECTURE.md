# The Garden Protocol: Curator's Field Guide & Information Architecture

> *"Consolidating human knowledge as a public commons—deterministic, homeostatic, and free from enclosure."*

## 1. Overview & Philosophy

The **Lumen / Hoshi Ecosystem** (`@thefourceprinciples`) is a local-first **Knowledge Operating System (KOS)** and **Information Architecture (IA)** built to organize, verify, and synthesize cross-domain knowledge without reliance on proprietary cloud gatekeepers. 

Rather than treating knowledge as static text blobs or unverified neural outputs, the **Garden Protocol** models information as a living, self-regulating ecology—combining deterministic verification graphs, content-addressable storage, non-hierarchical mycelial linking, and epistemological composting.

---

## 2. Ecosystem Topology (The 6 Core Modules)

The architecture spans four interdependent layers across six core repositories:

| Layer | Repository | Primary Stack | Core Function |
| :--- | :--- | :--- | :--- |
| **1. Mathematical & Logical Bedrock** | [`fource-cuc-core`](https://github.com) | Python (Zero-Dependency) | Implements Fource/CUC Algebra (`PFA`, `CS`, `COA`), the CUC Virtual Machine, and Phase-Locked Neural Networks. |
| **2. Deterministic Verification** | [`fource-md-kernel`](https://github.com) | Python 3 | Deterministic Directed Acyclic Graph (DAG) verification kernel for Modern Machine Design (`CIF-MD-000`) and strict state validation. |
| **3. Physical & Multimodal Diagnostics** | [`aero-scale-diag`](https://github.com) & [`hte-resonance-observatory`](https://github.com) | HTML / JS / Scientific Diagnostics | **Aero-Diag:** Dyadic scale-redistribution diagnostics for detecting flow separation, buffet onset, and grid aliasing in CFD velocity fields.<br>**HTE Observatory:** Multimodal materials exploration via visualization, sonification, harmonic coordinate mapping, and experiment ledgers. |
| **4. Homeostatic Cognitive Runtime** | [`Lumen`](https://github.com) & [`hoshi-engine`](https://github.com) | JavaScript / Python (Flask + SQLite) | **Lumen:** Homeostatic AI agent runtime for self-correcting autonomous reasoning.<br>**Hoshi Engine:** Local-first cognitive archive, parser/router, and SQLite state ledger. |

---

## 3. The Garden Protocol as Information Architecture (IA)

While a traditional Knowledge Operating System manages storage and retrieval, the **Garden Protocol** defines the structural Information Architecture that makes complex, multi-disciplinary data intelligible and auditable:

### Core IA Primitives

* **Entity (`Delta Fragments & Sources`):** Every discrete concept, empirical observation, historical sweep (`FR-XXX`), or diagnostic run is modeled as an atomic, addressable unit rather than an unstructured wall of text.
* **Record (`CAS Minimalist Datasheets & DAG Nodes`):** Entities are encapsulated in compact, standardized Content-Addressable Storage (CAS) datasheets and immutable DAG ledger nodes recording state, constraints, and provenance.
* **Identifiers (`Content Hashes & Pinakes Coordinates`):** Every record is bound to deterministic cryptographic hashes alongside **Pinakes / Dewey-style shelfmark coordinates**, guaranteeing exact lookup and zero ambiguity across distributed nodes.
* **Relationships (`Mycelial Linking`):** Unlike rigid folder trees that trap ideas inside single categories, **Mycelial Linking** establishes non-hierarchical, associative threads connecting disparate domains (e.g., fluid dynamics, harmonic resonance, and formal logic) beneath the surface.
* **Taxonomy (`The Almanac & Pinakes Index`):** Provides structured, human-navigable entry points—organizing validated knowledge chronologically, thematically, and by domain so curators can traverse the graph without losing context.

### Epistemological Lifecycle: Growth, Harvest & Composting

1. **Seeding & Ingestion:** Raw queries, external documents, or diagnostic telemetry enter through `hoshi/parser.py` and `hoshi/router.py` at tiered Water/hydration levels (Level 1 raw capture -> Level 3 deep synthesis).
2. **Verification & Homeostasis:** Claims and state transitions pass through `fource-md-kernel` and `Lumen`'s homeostatic loop to detect drift, contradiction, or ungrounded assertions.
3. **Harvest (`GARDEN HARVEST`):** Coherent, verified syntheses crystallize into portable **Almanac entries**, reproducible **experiment ledgers**, and **CAS datasheets**.
4. **Composting (`GARDEN COMPOST`):** Outdated, noisy, or falsified fragments are never silently deleted (`DROP`). Instead, they undergo **composting**—stripped of false certainty and recycled into structural metadata, negative-constraint baselines, and error logs that enrich future queries.

---

## 4. Data Flow Pipeline

```text
[ Raw Data / Telemetry / Inquiry ]
               │
               ▼
┌──────────────────────────────┐
│  hoshi/parser.py & router.py │  <-- Ingestion & Pinakes Coordinate Assignment
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  fource-cuc-core & md-kernel │  <-- CUC Algebra & Deterministic DAG Verification
└──────────────┬───────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
[ Validated ]   [ Anomalous / Stale ]
        │             │
        ▼             ▼
  GARDEN HARVEST   GARDEN COMPOST
 (CAS Datasheets  (Recycled into Error
  & Almanac)       Baselines & Logs)
```

---

## 5. Curator & Contributor Guidelines

* **Zero Hardcoded Secrets:** All API keys (e.g., `GEMINI_API_KEY`) and local database paths must remain in `.env` (excluded via `.gitignore`) or browser `localStorage`. Never commit live credentials.
* **Benchmark Reproducibility:** Diagnostic modules (`aero-scale-diag`, `hte-resonance-observatory`) prioritize deterministic, zero-dependency verification so independent mathematicians, physicists, and engineers can audit results directly.
* **Licensing (Anti-Enclosure):** All core codebases in this ecosystem are licensed under **GNU Affero General Public License v3.0 (AGPLv3)** to ensure that improvements and network-hosted derivatives remain open to humanity forever.
