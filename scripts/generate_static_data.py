#!/usr/bin/env python3
"""Generate static JSON data files from investment/*.md for Cloudflare Pages."""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INVESTMENT_DIR = REPO_ROOT / "investment"
PUBLIC_DIR = REPO_ROOT / "public"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


def main() -> None:
    PUBLIC_DIR.mkdir(exist_ok=True)

    dates = sorted(
        (f.stem for f in INVESTMENT_DIR.iterdir() if DATE_RE.match(f.name)),
        reverse=True,
    )

    reports = {}
    for d in dates:
        md_path = INVESTMENT_DIR / f"{d}.md"
        reports[d] = md_path.read_text(encoding="utf-8")

    (PUBLIC_DIR / "reports.json").write_text(
        json.dumps({"reports": dates, "data": reports}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Generated public/reports.json with {len(dates)} reports")


if __name__ == "__main__":
    main()
