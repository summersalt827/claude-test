#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

LOG_PREFIX="[investment-daily]"
MAX_RETRIES=3
TIMEOUT_SECS=120
NOTIFY_FORCE="${INVESTMENT_NOTIFY_FORCE:-0}"

notify_user() {
  local title="$1"
  local message="$2"
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"${message}\" with title \"${title}\"" >/dev/null 2>&1 || true
  fi
}

is_weekday() {
  local dow
  dow="$(date '+%u')"
  [ "$dow" -ge 1 ] && [ "$dow" -le 5 ]
}

is_trading_hours() {
  local hm
  hm="$(date '+%H%M')"
  # A股常规交易时段：09:30-11:30, 13:00-15:00
  if [ "$hm" -ge 0930 ] && [ "$hm" -le 1130 ]; then
    return 0
  fi
  if [ "$hm" -ge 1300 ] && [ "$hm" -le 1500 ]; then
    return 0
  fi
  return 1
}

has_data_degradation() {
  local today raw_file
  today="$(date '+%Y-%m-%d')"
  raw_file="$SCRIPT_DIR/../investment/raw/${today}-news.md"
  if [ ! -f "$raw_file" ]; then
    return 1
  fi
  /usr/bin/env python3 - "$raw_file" <<'PY'
import sys
from pathlib import Path

raw = Path(sys.argv[1])
text = raw.read_text(encoding="utf-8")
if "主备源失败" in text or "接口异常" in text:
    raise SystemExit(0)
raise SystemExit(1)
PY
}

should_notify_degradation() {
  if [ "$NOTIFY_FORCE" = "1" ]; then
    return 0
  fi
  is_weekday && is_trading_hours
}

push_to_feishu() {
  if /usr/bin/env python3 "$SCRIPT_DIR/send_investment_feishu_mcp.py"; then
    echo "$LOG_PREFIX feishu webhook push success"
    return 0
  fi
  echo "$LOG_PREFIX feishu webhook push failed"
  notify_user "投资日报推送失败" "日报已生成，但飞书 Webhook 推送失败，请检查日志。"
  return 1
}

push_email() {
  if /usr/bin/env python3 "$SCRIPT_DIR/send_investment_email.py"; then
    echo "$LOG_PREFIX email push success"
    return 0
  fi
  echo "$LOG_PREFIX email push failed"
  notify_user "投资日报邮件推送失败" "日报已生成，但邮件发送失败，请检查日志。"
  return 1
}

echo "$LOG_PREFIX start $(date '+%Y-%m-%d %H:%M:%S')"

attempt=1
while [ "$attempt" -le "$MAX_RETRIES" ]; do
  echo "$LOG_PREFIX attempt $attempt/$MAX_RETRIES"
  if command -v timeout >/dev/null 2>&1; then
    if timeout "$TIMEOUT_SECS" /usr/bin/env python3 "$SCRIPT_DIR/generate_investment_daily.py"; then
      echo "$LOG_PREFIX success on attempt $attempt"
      if has_data_degradation; then
        if should_notify_degradation; then
          notify_user "投资日报已生成（降级）" "数据抓取部分失败，已使用兜底内容。请开盘前复核。"
        else
          echo "$LOG_PREFIX degradation detected (silent outside trading hours)"
        fi
      fi
      push_to_feishu || true
      push_email || true
      exit 0
    fi
  else
    if /usr/bin/env python3 "$SCRIPT_DIR/generate_investment_daily.py"; then
      echo "$LOG_PREFIX success on attempt $attempt"
      if has_data_degradation; then
        if should_notify_degradation; then
          notify_user "投资日报已生成（降级）" "数据抓取部分失败，已使用兜底内容。请开盘前复核。"
        else
          echo "$LOG_PREFIX degradation detected (silent outside trading hours)"
        fi
      fi
      push_to_feishu || true
      push_email || true
      exit 0
    fi
  fi

  echo "$LOG_PREFIX failed on attempt $attempt"
  if [ "$attempt" -lt "$MAX_RETRIES" ]; then
    sleep 2
  fi
  attempt=$((attempt + 1))
done

echo "$LOG_PREFIX all attempts failed"
notify_user "投资日报生成失败" "自动任务已重试 ${MAX_RETRIES} 次，请检查日志。"
exit 1
