#!/usr/bin/env python3
"""Push investment report to Feishu via webhook."""

from __future__ import annotations

import datetime
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INVESTMENT_DIR = REPO_ROOT / "investment"

FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/296343c1-db65-4597-9ff2-f28017f0aff6"
VERCEL_BASE_URL = "https://claude-test-blush.vercel.app"


def main() -> None:
    today = datetime.date.today().isoformat()
    md_path = INVESTMENT_DIR / f"{today}.md"
    if not md_path.is_file():
        print(f"No investment file for today: {md_path}", file=sys.stderr)
        sys.exit(1)

    text = md_path.read_text(encoding="utf-8")
    text = f"【投资日报 {today}】\n\n{text}"
    text += f"\n\n查看完整日报：{VERCEL_BASE_URL}/#date={today}"
    max_chars = 14_500
    if len(text) > max_chars:
        text = text[: max_chars - 20] + "\n\n…(已截断)"

    payload = {"msg_type": "text", "content": {"text": text}}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        FEISHU_WEBHOOK,
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
