#!/usr/bin/env python3
"""Push investment report to Hyscandy@163.com via SMTP."""

from __future__ import annotations

import datetime
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INVESTMENT_DIR = REPO_ROOT / "investment"

SMTP_HOST = "smtp.163.com"
SMTP_PORT = 465
SENDER = "Hyscandy@163.com"
RECEIVER = "Hyscandy@163.com"


def get_smtp_password() -> str:
    password = os.environ.get("SMTP_163_PASSWORD", "").strip()
    if password:
        return password
    secret_file = Path.home() / ".smtp_163_password"
    if secret_file.is_file():
        return secret_file.read_text(encoding="utf-8").strip()
    print("Missing SMTP password. Set SMTP_163_PASSWORD env or create ~/.smtp_163_password", file=sys.stderr)
    sys.exit(1)


def md_to_html(md_text: str) -> str:
    lines = []
    in_list = False
    for line in md_text.splitlines():
        stripped = line.strip()
        if not stripped:
            if in_list:
                lines.append("</ul>")
                in_list = False
            lines.append("<br>")
            continue
        if stripped.startswith("# "):
            lines.append(f"<h1 style='font-size:22px;border-bottom:2px solid #2563eb;padding-bottom:6px;'>{stripped[2:]}</h1>")
        elif stripped.startswith("## "):
            lines.append(f"<h2 style='font-size:18px;color:#2563eb;margin:20px 0 8px;'>{stripped[3:]}</h2>")
        elif stripped.startswith("### "):
            lines.append(f"<h3 style='font-size:16px;margin:14px 0 6px;'>{stripped[4:]}</h3>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                lines.append("<ul>")
                in_list = True
            item = stripped[2:]
            import re
            item = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item)
            lines.append(f"<li style='margin:4px 0;'>{item}</li>")
        elif stripped.startswith("---"):
            lines.append("<hr style='border:none;border-top:1px solid #e5e7eb;margin:20px 0;'>")
        else:
            import re
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
            text = re.sub(r"`(.+?)`", r"<code style='background:#f3f4f6;padding:1px 4px;border-radius:3px;font-size:13px;'>\1</code>", text)
            lines.append(f"<p style='margin:6px 0;font-size:15px;line-height:1.7;'>{text}</p>")
    if in_list:
        lines.append("</ul>")
    return "\n".join(lines)


def main() -> None:
    today = datetime.date.today().isoformat()
    md_path = INVESTMENT_DIR / f"{today}.md"
    if not md_path.is_file():
        print(f"No investment file for today: {md_path}", file=sys.stderr)
        sys.exit(1)

    md_text = md_path.read_text(encoding="utf-8")
    password = get_smtp_password()
    html_body = md_to_html(md_text)

    page_url = "https://claude-test-euz.pages.dev"
    full_html = f"""\
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Noto Sans SC',sans-serif;max-width:720px;margin:0 auto;padding:20px;color:#1a1a1a;">
<h1 style="font-size:24px;margin-bottom:4px;">投资日报 {today}</h1>
<p style="color:#666;font-size:13px;margin-bottom:20px;">
<a href="{page_url}/#date={today}" style="color:#2563eb;">在网页中查看完整日报 →</a>
</p>
<hr style="border:none;border-top:1px solid #e5e7eb;margin:16px 0;">
{html_body}
<hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;">
<p style="color:#999;font-size:12px;">
免责声明：以上建议仅供参考，不构成投资建议。投资有风险，入市需谨慎。<br>
数据来源：证券时报、新华财经、四大证券报摘要
</p>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"投资日报 {today}"
    msg["From"] = SENDER
    msg["To"] = RECEIVER

    md_text_with_link = md_text + f"\n\n查看完整日报：{page_url}/#date={today}"
    msg.attach(MIMEText(md_text_with_link, "plain", "utf-8"))
    msg.attach(MIMEText(full_html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.login(SENDER, password)
            server.sendmail(SENDER, [RECEIVER], msg.as_string())
    except Exception as exc:
        print(f"Email send failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Email sent to {RECEIVER} for {today}")


if __name__ == "__main__":
    main()
