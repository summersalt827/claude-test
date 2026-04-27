#!/usr/bin/env python3
"""Send investment/YYYY-MM-DD.md to Feishu custom bot."""

from __future__ import annotations

import datetime
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INVESTMENT_DIR = REPO_ROOT / "investment"


def main() -> None:
    webhook = os.environ.get("FEISHU_WEBHOOK", "").strip()
    if not webhook:
        print("Missing env FEISHU_WEBHOOK", file=sys.stderr)
        sys.exit(1)

    today = datetime.date.today().isoformat()
    md_path = INVESTMENT_DIR / f"{today}.md"
    if not md_path.is_file():
        print(f"No investment file for today: {md_path}", file=sys.stderr)
        sys.exit(1)

    text = md_path.read_text(encoding="utf-8")
    text = f"【投资日报 {today}】\n\n{text}"

    # Keep enough room for title wrapper.
    max_chars = 14_500
    if len(text) > max_chars:
        text = text[: max_chars - 20] + "\n\n…(已截断)"

    payload = {"msg_type": "text", "content": {"text": text}}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        sys.exit(1)

    print(body)
    try:
        obj = json.loads(body)
    except json.JSONDecodeError:
        return

    status = obj.get("StatusCode")
    if status is not None and status != 0:
        print(body, file=sys.stderr)
        sys.exit(1)
    code = obj.get("code")
    if code is not None and code != 0:
        print(body, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
