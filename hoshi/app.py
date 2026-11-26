from __future__ import annotations

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
from .parser import normalize_text, parse_signal
from .router import chronovisor_query, engine_step

APP_NAME = "Hoshi Identity Engine"


def create_app() -> Flask:
    init_db()
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
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
</style></head><body><div class="wrap">
  <h1>{{ app_name }}</h1>
  <div class="grid">
    <div class="panel"><h2>Signal Console</h2>
      <form method="post" action="{{ url_for('index') }}">
        <textarea name="text" placeholder="Send Hoshi a signal, task, timeline prompt, or manifest...">{{ prefill_text }}</textarea>
        <button type="submit">Process Signal</button>
      </form>
      {% if last_result %}<p><strong>Response:</strong> {{ last_result.response_text }}</p>{% endif %}
    </div>
    <div class="panel"><h2>Active State</h2>
      <p>Mode: <strong>{{ state.identity_mode }}</strong> | Subspace: <strong>{{ state.active_subspace }}</strong></p>
      <p>Coherence: <strong>{{ state.coherence_score }}</strong> | Constraint: <strong>{{ state.constraint_score }}</strong> | Fource: <strong>{{ state.fource_score }}</strong></p>
      <div>{% for c in state.active_capsules %}<span class="pill">{{ c }}</span>{% endfor %}</div>
    </div>
    <div class="panel"><h2>Recent Memory</h2>
      {% for m in memories %}<div style="border-bottom:1px solid #30363d;padding:6px 0;"><strong>{{ m.memory_kind }}</strong>: {{ m.text[:140] }}</div>{% endfor %}
    </div>
  </div>
</div></body></html>"""
