#!/usr/bin/env python3
"""Script de prueba para el cliente `client_stream`.

Hace una petición POST a `/stream` con la API key tomada desde `.env`
y consume la respuesta en modo streaming (SSE), mostrando los chunks
en tiempo real.

Uso:
    python scripts/client_stream.py --message "Hola" --max-tokens 150
"""
import argparse
import asyncio
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


async def stream_request(url: str, api_key: str, message: str, max_tokens: int) -> None:
    payload = {
        "messages": [{"role": "user", "content": message}],
        "max_tokens": max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            async with client.stream("POST", url, headers=headers, json=payload, timeout=60.0) as resp:
                print(f"HTTP {resp.status_code}")

                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    # SSE lines typically like: data: <payload>
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk == "[DONE]":
                            print("\n[DONE]")
                            return
                        # intentar parsear JSON dentro del data
                        try:
                            parsed = json.loads(chunk)
                            print(json.dumps(parsed, indent=2, ensure_ascii=False))
                        except Exception:
                            # imprimir chunk tal cual
                            print(chunk, end="", flush=True)
        except Exception as e:
            print(f"Request error: {e}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cliente streaming contra /stream")
    parser.add_argument("--message", "-m", default="Explica qué es Redis", help="Mensaje del usuario")
    parser.add_argument("--max-tokens", "-n", type=int, default=200, help="Max tokens")
    parser.add_argument("--url", "-u", default="http://localhost:8000/stream", help="URL del endpoint")
    args = parser.parse_args()

    api_key = load_api_key()

    asyncio.run(stream_request(args.url, api_key, args.message, args.max_tokens))


if __name__ == "__main__":
    main()
