"""Quick check that ANTHROPIC_API_KEY in .env works — avoids curl/PowerShell quoting.

Run:  uv run python scripts/check_anthropic_key.py

Uses truststore so the request trusts the OS (Windows) certificate store, which gets
past a TLS-intercepting proxy/AV the same way `uv --system-certs` does.
"""

from __future__ import annotations

import sys

import truststore

truststore.inject_into_ssl()  # use the OS cert store (handles the corporate TLS proxy)

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import anthropic  # noqa: E402


def main() -> int:
    try:
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the env/.env
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=16,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
        )
    except anthropic.AuthenticationError:
        print("FAIL: authentication failed - the API key is invalid or revoked.")
        return 1
    except anthropic.PermissionDeniedError:
        print("FAIL: key is valid but lacks permission (check Console billing/credits).")
        return 1
    except anthropic.APIConnectionError as exc:
        print(f"FAIL: could not connect (likely TLS/proxy): {exc}")
        return 1
    except anthropic.APIStatusError as exc:
        print(f"FAIL: API error {exc.status_code}: {exc.message}")
        return 1

    text = next((b.text for b in resp.content if b.type == "text"), "")
    print(f"OK: API key works. Model replied: {text.strip()!r}")
    print(f"   input/output tokens: {resp.usage.input_tokens}/{resp.usage.output_tokens}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
