# Hoshi Engine

## Looking for collaborators

This project is actively seeking 1–3 collaborators to help stabilize and modularize the current prototype. See "What Needs Work" below for details.

Hoshi is a local-first, stateful cognitive archive built with Flask and SQLite.

It is designed to preserve structured memory, track identity over time, and route reasoning across internal modes instead of treating every interaction as a stateless input/output exchange.

## Current Status

Hoshi currently exists as a working prototype implemented in a single file:

- `app_identity.py`

The system already includes:

- signal parsing
- identity state tracking
- memory and archive storage
- subspace routing
- event and bridge logging
- Chronovisor scaffolding
- local SQLite persistence
- basic Flask routes and dashboard behavior

## Core Idea

Most systems follow a simple pattern:

`input -> output`

Hoshi instead follows a stateful path more like:

`input -> parsed signal -> routed state -> memory / identity / archive -> output`

The goal is to preserve continuity, provenance, and structure over time.

## Current Architecture

### Application Layer
- Flask app
- local dashboard
- API routes

### Core Logic
- signal parser
- subspace router
- identity engine
- memory/archive handling
- Chronovisor scaffold

### Persistence

Current prototype uses SQLite-backed persistence for:

- identity state
- parsed signals
- memory entries
- interaction logs
- subspace events
- bridges
- Chronovisor queries

## What Works Right Now

- local runtime  
- persistent memory  
- state tracking  
- subspace transitions  
- archive behavior  
- prototype routing structure  

## What Needs Work

The project is real, but still early. Immediate priorities are:

1. Modularize `app_identity.py` into a cleaner multi-file architecture  
2. Confirm and clean the canonical database/schema  
3. Improve signal parsing and routing consistency  
4. Add tests and migration safety  
5. Make the project easier for collaborators to understand and extend  

## Collaboration Goal

I am looking for a small number of careful collaborators who are comfortable with:

- Python  
- Flask  
- SQLite  
- refactoring messy but working prototypes  
- preserving behavior while improving structure  

This is not a rewrite-from-scratch project. The goal is to stabilize and extend the working system.

## Near-Term Refactor Direction

Planned module split:

- `app.py`  
- `db.py`  
- `parser.py`  
- `router.py`  
- `memory.py`  
- `identity.py`  
- `chronovisor.py`  

## Design Priorities

- local-first operation  
- identity continuity  
- memory provenance  
- clean archive behavior  
- explicit state transitions  
- safe iterative refactoring  

## Repository Notes

At the moment, this repository contains the active prototype file and project scaffolding. Additional documentation, issue tracking, and architectural cleanup are the next step.

## Getting Started (Current State)

This is a prototype. To run locally:

1. Ensure Python 3.10+ is installed  
2. Install Flask:
   ```bash
   pip install flask
