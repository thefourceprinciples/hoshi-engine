from __future__ import annotations

import os
from flask import Flask, jsonify, render_template_string, request, url_for

from . import __version__
from .db import (
    init_db,
    latest_identity_state,
    recent_chronovisor_queries,
    recent_events,
    recent_memories,
    recent_parsed_signals,
)
from .garden import list_garden_seeds, water_framework
from .parser import normalize_text, parse_signal
from .router import chronovisor_query, engine_step

APP_NAME = "Hoshi Identity Engine"
ALLOWED_ORIGINS = {
    "https://github.io",
    "http://127.0.0.1:5001",
    "http://localhost:5001",
}


def create_app() -> Flask:
    init_db()
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 256 * 1024  # 256 KB payload cap

    @app.before_request
    def verify_optional_token():
        expected = os.environ.get("HOSHI_API_TOKEN", "").strip()
        if expected and request.path.startswith("/api/") and request.method == "POST":
            provided = request.headers.get("X-Hoshi-Token", "").strip()
            if provided != expected:
                return jsonify({"error": "Unauthorized"}), 401

    @app.after_request
    def add_security_headers(response):
        origin = request.headers.get("Origin", "")
        if origin in ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Hoshi-Token"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.route("/", methods=["GET", "POST"])
    def index():
        last_result = None
        prefill_text = ""
        if request.method == "POST":
            prefill_text = request.form.get("text", "")
            if normalize_text(prefill_text):
                last_result = engine_step(prefill_text)
        return render_template_string(
            DASHBOARD_HTML,
            app_name=f"{APP_NAME} v{__version__}",
            state=latest_identity_state(),
            events=recent_events(),
            signals=recent_parsed_signals(),
            memories=recent_memories(),
            almanac=list_garden_seeds(),
            chronovisor_queries=recent_chronovisor_queries(),
            last_result=last_result,
            prefill_text=prefill_text,
        )

    @app.route("/api/respond", methods=["POST", "OPTIONS"])
    def api_respond():
        if request.method == "OPTIONS":
            return ("", 204)
        payload = request.get_json(silent=True) or {}
        text = payload.get("text", "")
        if not normalize_text(text):
            return jsonify({"error": "Missing text."}), 400
        return jsonify(engine_step(text))

    @app.route("/api/state", methods=["GET"])
    def api_state():
        return jsonify(latest_identity_state())

    @app.route("/api/timeline", methods=["POST", "OPTIONS"])
    def api_timeline():
        if request.method == "OPTIONS":
            return ("", 204)
        payload = request.get_json(silent=True) or {}
        text = payload.get("text", "")
        if not normalize_text(text):
            return jsonify({"error": "Missing text."}), 400
        signal = parse_signal(text)
        return jsonify(chronovisor_query(signal.normalized_text, signal))

    @app.route("/api/memory", methods=["GET"])
    def api_memory():
        return jsonify(recent_memories(limit=50))

    @app.route("/api/almanac", methods=["GET"])
    def api_almanac():
        return jsonify(list_garden_seeds())

    @app.route("/api/cas/<fr_id>", methods=["GET"])
    def api_cas(fr_id: str):
        res = water_framework(fr_id, level=1)
        if not res:
            return jsonify({"error": f"{fr_id} not found"}), 404
        return jsonify(res["cas_field_card"])

    @app.route("/health", methods=["GET"])
    def health():
        st = latest_identity_state()
        return jsonify({
            "status": "ok",
            "app": APP_NAME,
            "version": __version__,
            "active_subspace": st.get("active_subspace"),
            "coherence_score": st.get("coherence_score"),
        })

    return app


DASHBOARD_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ app_name }}</title>
<style>
  body { margin:0; font-family:system-ui,sans-serif; background:#0d1117; color:#e6edf3; padding:20px; }
  .wrap { max-width:1300px; margin:0 auto; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:16px; margin-top:16px; }
  .panel { background:#161b22; border:1px solid #30363d; border-radius:12px; padding:16px; }
  textarea { width:100%; min-height:140px; background:#0b0f14; color:#e6edf3; border:1px solid #30363d; border-radius:8px; padding:10px; }
  button { background:#58a6ff; color:#fff; border:0; border-radius:8px; padding:9px 14px; font-weight:700; cursor:pointer; margin-top:8px; }
  .pill { display:inline-block; padding:4px 9px; border-radius:999px; font-size:12px; border:1px solid #30363d; margin:2px; }
  pre { background:#0b0f14; padding:10px; border-radius:8px; overflow-x:auto; font-size:12px; white-space:pre-wrap; }
</style></head><body><div class="wrap">
  <h1>{{ app_name }}</h1>
  <div class="grid">
    <div class="panel"><h2>Signal &amp; Garden Console</h2>
      <form method="post" action="{{ url_for('index') }}">
        <textarea name="text" placeholder="Send a signal, Plant FR-001 | Name | Bed | Invariant, Water FR-001 at Level 2, or Garden Harvest...">{{ prefill_text }}</textarea>
        <button type="submit">Process Signal</button>
      </form>
      {% if last_result %}
        <p><strong>Response:</strong> {{ last_result.response_text }}</p>
        {% if last_result.structured_result %}<pre>{{ last_result.structured_result | tojson(indent=2) }}</pre>{% endif %}
      {% endif %}
    </div>
    <div class="panel"><h2>Active State</h2>
      <p>Mode: <strong>{{ state.identity_mode }}</strong> | Subspace: <strong>{{ state.active_subspace }}</strong></p>
      <p>Coherence: <strong>{{ state.coherence_score }}</strong> | Constraint: <strong>{{ state.constraint_score }}</strong> | Fource: <strong>{{ state.fource_score }}</strong></p>
      <div>{% for c in state.active_capsules %}<span class="pill">{{ c }}</span>{% endfor %}</div>
    </div>
    <div class="panel"><h2>The Farmer's Almanac ({{ almanac | length }})</h2>
      {% for s in almanac %}<div style="border-bottom:1px solid #30363d;padding:6px 0;"><strong>{{ s.framework_id }} · {{ s.name }}</strong> [{{ s.status }}]<br><small>{{ s.almanac_shelfmark }}</small></div>{% else %}<p style="color:#8b949e;">No seeds planted yet. Try: <code>Plant FR-001 | Hoshi Core | KERNEL | Local-first stateful memory router.</code></p>{% endfor %}
    </div>
    <div class="panel"><h2>Recent Memory</h2>
      {% for m in memories %}<div style="border-bottom:1px solid #30363d;padding:6px 0;"><strong>{{ m.memory_kind }}</strong>: {{ m.text[:140] }}</div>{% endfor %}
    </div>
  </div>
</div></body></html>"""
