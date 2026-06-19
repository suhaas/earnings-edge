"""Validate COMPOSIO_API_KEY and report whether Gmail is connected for COMPOSIO_USER_ID.

Run:
  uv run python scripts/check_composio_key.py                  # check key + Gmail status
  uv run python scripts/check_composio_key.py --connect-gmail  # print an OAuth URL to connect Gmail

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


def _toolkit_slug(item: dict) -> str:
    tk = item.get("toolkit")
    if isinstance(tk, dict):
        return str(tk.get("slug") or tk.get("name") or "").lower()
    return str(tk or item.get("toolkit_slug") or "").lower()


def _items(resp: object) -> list[dict]:
    data = resp.model_dump() if hasattr(resp, "model_dump") else resp
    if isinstance(data, dict):
        for key in ("items", "data", "connected_accounts", "results"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return data if isinstance(data, list) else []


def main() -> int:
    user_id = os.environ.get("COMPOSIO_USER_ID", "default")
    if not os.environ.get("COMPOSIO_API_KEY"):
        print("FAIL: COMPOSIO_API_KEY is not set in .env.")
        return 1

    client = Composio()

    # 1) Validate the key with a tiny authenticated call.
    try:
        client.connected_accounts.list(limit=1)
    except Exception as exc:
        msg = str(exc)
        if any(s in msg for s in ("401", "Unauthorized", "Invalid API key")):
            print("FAIL: COMPOSIO_API_KEY is invalid (401). Regenerate it in the Composio dashboard.")
        else:
            print(f"FAIL: could not reach Composio ({type(exc).__name__}: {msg[:120]})")
        return 1
    print(f"OK: COMPOSIO_API_KEY is valid.  (user_id = {user_id})")

    # 2) Optional: start the Gmail OAuth connection and print the URL to visit.
    if "--connect-gmail" in sys.argv:
        try:
            req = client.toolkits.authorize(user_id=user_id, toolkit="gmail")
        except Exception as exc:
            print(f"FAIL: could not start Gmail authorization ({type(exc).__name__}: {exc})")
            return 1
        url = getattr(req, "redirect_url", None) or getattr(req, "redirectUrl", None)
        print("\nOpen this URL in your browser, authorize Gmail, then re-run the check:")
        print(" ", url or repr(req))
        return 0

    # 3) Report Gmail connection status for this user.
    resp = client.connected_accounts.list(user_ids=[user_id])
    items = _items(resp)
    gmail = [it for it in items if _toolkit_slug(it) == "gmail"]
    active = [it for it in gmail if str(it.get("status", "")).upper() == "ACTIVE"]
    print(f"connections for {user_id}: {len(items)} total | gmail: {len(gmail)} (active: {len(active)})")
    if active:
        print("OK: Gmail is connected and ACTIVE -> delivery should work.")
        return 0
    print("ACTION: Gmail is not connected for this user.")
    print("  Run:  uv run python scripts/check_composio_key.py --connect-gmail")
    return 0


if __name__ == "__main__":
    sys.exit(main())
