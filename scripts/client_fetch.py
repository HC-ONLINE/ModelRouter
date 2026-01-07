#!/usr/bin/env python3
"""Script de prueba para el cliente `client_fetch`.

Hace una petición POST a `/chat` con la API key tomada desde `.env`
y muestra la respuesta formateada.

Uso:
  python scripts/client_fetch.py --message "Hola" --max-tokens 150
"""
import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


def load_api_key() -> str:
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
    api_key = os.getenv("API_KEY")
    if not api_key:
        print("ERROR: API_KEY not found in .env", file=sys.stderr)
        sys.exit(2)
    return api_key


def main() -> None:
    parser = argparse.ArgumentParser(description="Prueba cliente fetch contra /chat")
    parser.add_argument("--message", "-m", default="Explica qué es Redis", help="Mensaje del usuario")
    parser.add_argument("--max-tokens", "-n", type=int, default=150, help="Max tokens")
    parser.add_argument("--url", "-u", default="http://localhost:8000/chat", help="URL del endpoint")
    args = parser.parse_args()

    api_key = load_api_key()

    payload = {
        "messages": [{"role": "user", "content": args.message}],
        "max_tokens": args.max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = httpx.post(args.url, json=payload, headers=headers, timeout=30.0)
    except Exception as e:
        print(f"Request error: {e}", file=sys.stderr)
        sys.exit(3)

    print(f"HTTP {resp.status_code}")
    try:
        body = resp.json()
        print(json.dumps(body, indent=2, ensure_ascii=False))
    except Exception:
        # Fallback: imprimir texto crudo
        print(resp.text)


if __name__ == "__main__":
    main()
