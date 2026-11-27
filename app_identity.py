from __future__ import annotations

import json
import os

from hoshi.app import APP_NAME, create_app
from hoshi.db import init_db
from hoshi.parser import normalize_text
from hoshi.router import engine_step

app = create_app()


def run_cli() -> None:
    print(f"{APP_NAME} ready. Type 'exit' to quit.\n")
    while True:
        try:
            text = input("Hoshi > ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting Hoshi.")
            break
        if text.strip().lower() in {"exit", "quit"}:
            print("Exiting Hoshi.")
            break
        if not normalize_text(text):
            continue
        result = engine_step(text)
        print(json.dumps(result["state"], indent=2, ensure_ascii=False))
        print(f"\nHoshi says: {result['response_text']}\n")


def main() -> None:
    init_db()
    if os.environ.get("HOSHI_WEB", "0") == "1":
        debug_mode = os.environ.get("HOSHI_DEBUG", "0") == "1"
        app.run(host="127.0.0.1", port=5001, debug=debug_mode)
    else:
        run_cli()


if __name__ == "__main__":
    main()
