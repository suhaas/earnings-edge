"""Validate COMPOSIO_API_KEY and start the Gmail connection for COMPOSIO_USER_ID.

Run:
  uv run python scripts/check_composio_key.py

Composio's read/list endpoints do NOT return 401 for a bad key (they return public/empty
data), so we validate with `toolkits.authorize` — a real authenticated operation that both
checks the key and starts the Gmail OAuth flow. On success it prints a URL to authorize.

Uses truststore (OS cert store) so it works behind a TLS-inspecting proxy.
"""

from __future__ import annotations

import os
import sys

import truststore

truststore.inject_into_ssl()

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from composio import Composio  # noqa: E402


def main() -> int:
    user_id = os.environ.get("COMPOSIO_USER_ID", "default")
    if not os.environ.get("COMPOSIO_API_KEY"):
        print("FAIL: COMPOSIO_API_KEY is not set in .env.")
        return 1

    client = Composio()

    # Validate with an authenticated write op (reads don't 401 on a bad key). This also
    # starts the Gmail connection and returns a URL to authorize it.
    try:
        req = client.toolkits.authorize(user_id=user_id, toolkit="gmail")
    except Exception as exc:
        msg = str(exc)
        if any(s in msg for s in ("401", "Unauthorized", "Invalid API key")):
            print("FAIL: COMPOSIO_API_KEY is INVALID (401).")
            print("  Regenerate it in the Composio dashboard (Settings -> API Keys),")
            print("  then update COMPOSIO_API_KEY in .env and re-run this script.")
        else:
            print(f"FAIL: could not reach Composio ({type(exc).__name__}: {msg[:140]})")
        return 1

    url = getattr(req, "redirect_url", None) or getattr(req, "redirectUrl", None)
    print(f"OK: COMPOSIO_API_KEY is valid.  (user_id = {user_id})")
    print("\nConnect Gmail: open this URL in your browser and authorize, then re-run the app:")
    print(" ", url or repr(req))
    return 0


if __name__ == "__main__":
    sys.exit(main())
