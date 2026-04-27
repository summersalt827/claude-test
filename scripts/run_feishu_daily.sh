#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SECRET="${FEISHU_WEBHOOK_FILE:-$HOME/.feishu_daily_webhook}"
if [[ -z "${FEISHU_WEBHOOK:-}" && -f "$SECRET" ]]; then
  export FEISHU_WEBHOOK="$(tr -d ' \t\n\r' < "$SECRET")"
fi
exec /usr/bin/env python3 "$SCRIPT_DIR/send_daily_feishu.py"
