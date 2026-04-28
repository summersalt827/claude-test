#!/usr/bin/env python3
"""Generate a daily A-share investment note with market snapshots."""

from __future__ import annotations

import datetime
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INVESTING_PREF_PATH = REPO_ROOT / "investing.md"
DAILY_NEWS_DIR = REPO_ROOT / "daily_news"
INVESTMENT_DIR = REPO_ROOT / "investment"
RAW_DIR = INVESTMENT_DIR / "raw"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
}


@dataclass
class IndexPoint:
    name: str
    latest: float | None
    pct: float | None
    change: float | None
    amount: float | None


def fetch_json(url: str, params: dict[str, str] | None = None) -> dict:
    query = f"{url}?{urllib.parse.urlencode(params)}" if params else url
    req = urllib.request.Request(query, headers=DEFAULT_HEADERS)
    with urllib.request.urlopen(req, timeout=12) as resp:
        payload = resp.read().decode("utf-8", errors="ignore")
        return json.loads(payload)


def fetch_text(url: str, params: dict[str, str] | None = None, encoding: str = "utf-8") -> str:
    query = f"{url}?{urllib.parse.urlencode(params)}" if params else url
    req = urllib.request.Request(query, headers=DEFAULT_HEADERS)
    with urllib.request.urlopen(req, timeout=12) as resp:
        payload = resp.read()
    return payload.decode(encoding, errors="ignore")


def retry_call(func, attempts: int = 2, delay_sec: float = 0.8):
    last_exc = None
    for idx in range(attempts):
        try:
            return func()
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            last_exc = exc
            if idx < attempts - 1:
                time.sleep(delay_sec)
    if last_exc:
        raise last_exc
    raise RuntimeError("retry_call reached an unexpected state")


def safe_float(value: object) -> float | None:
    try:
        if value is None or value == "-":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def load_investing_summary() -> list[str]:
    if not INVESTING_PREF_PATH.is_file():
        return ["- 未找到 investing.md，请先补充投资偏好配置。"]

    lines = INVESTING_PREF_PATH.read_text(encoding="utf-8").splitlines()
    bullets: list[str] = []
    for raw in lines:
        line = raw.strip()
        if line.startswith("- ") or line.startswith("* "):
            cleaned = line[2:].strip()
            cleaned = cleaned.replace("**", "")
            bullets.append(f"- {cleaned}")
        if len(bullets) >= 8:
            break

    if not bullets:
        return ["- investing.md 已存在，但未提取到明确偏好条目。"]
    return bullets


def load_self_selected_funds() -> list[str]:
    """从 investing.md 提取自选基金代码列表。"""
    if not INVESTING_PREF_PATH.is_file():
        return []
    lines = INVESTING_PREF_PATH.read_text(encoding="utf-8").splitlines()
    funds: list[str] = []
    in_self_selected = False
    for raw in lines:
        line = raw.strip()
        if "自选基金" in line:
            in_self_selected = True
            continue
        if in_self_selected:
            if line.startswith("- ") or line.startswith("* "):
                import re
                m = re.search(r"(\d{6})", line)
                if m:
                    funds.append(m.group(1))
            elif line.startswith("#") or (line and not line.startswith("-") and not line.startswith("*") and not line.startswith(" ")):
                break
    return funds


def fetch_fund_nav(fund_code: str) -> tuple[dict | None, str | None]:
    """通过东方财富接口获取基金最新净值。"""
    try:
        url = f"https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"
        data = retry_call(lambda: fetch_text(url, encoding="utf-8"))
        import re
        # 提取基金名称
        name_match = re.search(r'fS_name\s*=\s*"([^"]+)"', data)
        name = name_match.group(1) if name_match else "未知基金"
        # 提取最新净值
        nav_match = re.search(r'fS_code\s*=\s*"([^"]+)"', data)
        nav_code = nav_match.group(1) if nav_match else fund_code
        # 提取净值走势（最新一条）
        nav_list_match = re.search(r'Data_netWorthTrend\s*=\s*\[(.*?)\];', data, re.DOTALL)
        if nav_list_match:
            import json as _json
            nav_data = _json.loads(f"[{nav_list_match.group(1)}]")
            if nav_data:
                latest = nav_data[-1]
                nav_date_ts = latest.get("x", 0) / 1000
                import datetime as _dt
                nav_date = _dt.datetime.fromtimestamp(nav_date_ts).strftime("%Y-%m-%d")
                nav = latest.get("y", "N/A")
                # 计算涨跌幅
                if len(nav_data) >= 2:
                    prev = nav_data[-2].get("y", 0)
                    if prev and prev != 0:
                        growth_rate = f"{((nav - prev) / prev * 100):.2f}"
                    else:
                        growth_rate = "N/A"
                else:
                    growth_rate = "N/A"
                return {
                    "code": nav_code,
                    "name": name,
                    "nav": f"{nav:.4f}",
                    "nav_date": nav_date,
                    "growth_rate": growth_rate,
                }, None
        return None, f"基金 {fund_code} 净值数据解析失败"
    except Exception as e:
        return None, f"基金 {fund_code} 抓取失败: {e}"


def build_self_selected_section(funds: list[str]) -> list[str]:
    """构建自选基金分析板块内容。"""
    if not funds:
        return ["- 当前未配置自选基金，请在 investing.md 的「自选基金」中添加。"]

    lines: list[str] = []
    for code in funds:
        info, err = fetch_fund_nav(code)
        if info:
            growth_rate = info.get("growth_rate", "N/A")
            try:
                rate_val = float(growth_rate)
                if rate_val > 0:
                    trend = "🟢 上涨"
                elif rate_val < 0:
                    trend = "🔴 下跌"
                else:
                    trend = "⚪ 平盘"
            except (ValueError, TypeError):
                trend = "⚪ 未知"
            lines.append(f"- **{info['name']}**（{info['code']}）：最新净值 {info['nav']}（{info['nav_date']}），近期涨跌 {growth_rate}% {trend}")
        else:
            lines.append(f"- **{code}**：{err}")

    return lines


def load_news_hint(today: str) -> list[str]:
    news_path = DAILY_NEWS_DIR / f"{today}.md"
    if not news_path.is_file():
        return ["- 当日新闻文件缺失：daily_news/YYYY-MM-DD.md。"]

    lines = news_path.read_text(encoding="utf-8").splitlines()
    hints: list[str] = []
    for raw in lines:
        line = raw.strip()
        if line.startswith("- ") or line.startswith("* "):
            hints.append(f"- {line[2:].strip()}")
        elif line[:3] in {"1. ", "2. ", "3. ", "4. ", "5. "}:
            hints.append(f"- {line[3:].strip()}")
        if len(hints) >= 8:
            break

    if not hints:
        return ["- 已检测到当日新闻，但未抽取到可用要点。"]
    return hints


def fetch_index_snapshot() -> tuple[list[IndexPoint], str | None]:
    try:
        data = retry_call(
            lambda: fetch_json(
                "https://push2.eastmoney.com/api/qt/ulist.np/get",
                {
                    "fltt": "2",
                    "invt": "2",
                    "fields": "f12,f14,f2,f3,f4,f6",
                    "secids": "1.000001,0.399001,0.399006",
                    "ut": "b2884a393a59ad64002292a3e90d46a5",
                },
            )
        )
        rows = (data.get("data") or {}).get("diff") or []
        result: list[IndexPoint] = []
        for row in rows:
            result.append(
                IndexPoint(
                    name=str(row.get("f14") or "未知指数"),
                    latest=safe_float(row.get("f2")),
                    pct=safe_float(row.get("f3")),
                    change=safe_float(row.get("f4")),
                    amount=safe_float(row.get("f6")),
                )
            )
        if not result:
            return [], "指数接口返回为空"
        return result, None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as primary_exc:
        try:
            # Fallback source: Tencent quote feed.
            payload = retry_call(
                lambda: fetch_text(
                    "https://qt.gtimg.cn/q",
                    {"q": "s_sh000001,s_sz399001,s_sz399006"},
                    encoding="gbk",
                )
            )
            rows = [line.strip() for line in payload.split(";") if line.strip()]
            parsed: list[IndexPoint] = []
            for row in rows:
                if "~" not in row:
                    continue
                parts = row.split("~")
                if len(parts) < 7:
                    continue
                parsed.append(
                    IndexPoint(
                        name=parts[1] or "未知指数",
                        latest=safe_float(parts[3]),
                        pct=safe_float(parts[5]),
                        change=safe_float(parts[4]),
                        amount=safe_float(parts[6]),
                    )
                )
            if parsed:
                return parsed, f"指数主源失败，已切换备源: {primary_exc}"
            return [], f"指数主备源均无有效数据，主源异常: {primary_exc}"
        except (urllib.error.URLError, TimeoutError, ValueError) as fallback_exc:
            return [], f"指数主备源失败: primary={primary_exc}; fallback={fallback_exc}"


def fetch_northbound_flow() -> tuple[dict[str, float | None], str | None]:
    try:
        data = retry_call(
            lambda: fetch_json(
                "https://push2.eastmoney.com/api/qt/kamt/get",
                {"fields1": "f1,f3", "fields2": "f51,f52,f53,f54,f55,f56,f57,f58"},
            )
        )
        row = data.get("data") or {}
        sh = safe_float(row.get("hk2sh"))
        sz = safe_float(row.get("hk2sz"))
        total = None
        if sh is not None and sz is not None:
            total = sh + sz
        return {"shanghai": sh, "shenzhen": sz, "total": total}, None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as primary_exc:
        try:
            # Fallback source: Eastmoney datacenter history (latest trading day net flow).
            data = retry_call(
                lambda: fetch_json(
                    "https://datacenter-web.eastmoney.com/api/data/v1/get",
                    {
                        "reportName": "RPT_MUTUAL_DEAL_HISTORY",
                        "columns": "ALL",
                        "sortColumns": "TRADE_DATE",
                        "sortTypes": "-1",
                        "pageNumber": "1",
                        "pageSize": "1",
                    },
                )
            )
            rows = (data.get("result") or {}).get("data") or []
            if not rows:
                return {}, f"北向资金主备源均无数据，主源异常: {primary_exc}"
            latest = rows[0]
            total = safe_float(latest.get("NET_DEAL_AMT"))
            return (
                {"shanghai": None, "shenzhen": None, "total": total},
                f"北向资金主源失败，已切换备源(日频): {primary_exc}",
            )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as fallback_exc:
            return {}, f"北向资金主备源失败: primary={primary_exc}; fallback={fallback_exc}"


def format_market_summary(indices: list[IndexPoint], northbound: dict[str, float | None]) -> list[str]:
    lines: list[str] = []
    if indices:
        for idx in indices:
            pct = "N/A" if idx.pct is None else f"{idx.pct:.2f}%"
            latest = "N/A" if idx.latest is None else f"{idx.latest:.2f}"
            lines.append(f"- {idx.name}：{latest} 点，涨跌幅 {pct}")
    else:
        lines.append("- 指数快照抓取失败，建议手动复核盘前指数。")

    total = northbound.get("total") if northbound else None
    if total is None:
        lines.append("- 北向资金抓取失败或未开盘，建议关注开盘后 30 分钟资金方向。")
    else:
        bias = "净流入" if total >= 0 else "净流出"
        lines.append(f"- 北向资金合计约 {total:.2f} 亿元（{bias}）。")
    return lines


def build_action_suggestions(indices: list[IndexPoint], northbound: dict[str, float | None]) -> list[str]:
    suggestion: list[str] = []
    risk = "中性"

    index_avg = None
    valid_pct = [it.pct for it in indices if it.pct is not None]
    if valid_pct:
        index_avg = sum(valid_pct) / len(valid_pct)

    nb_total = northbound.get("total") if northbound else None
    if (index_avg is not None and index_avg < -0.6) or (nb_total is not None and nb_total < -20):
        risk = "偏谨慎"
    elif (index_avg is not None and index_avg > 0.6) and (nb_total is not None and nb_total > 20):
        risk = "偏积极"

    if risk == "偏积极":
        suggestion.append("- 仓位建议：可从中性仓位逐步提升，优先分批而非一次性追高。")
        suggestion.append("- 操作节奏：优先布局强势主线 ETF 与龙头回踩机会。")
    elif risk == "偏谨慎":
        suggestion.append("- 仓位建议：控制总仓位，新增仓位以防守型品种为主。")
        suggestion.append("- 操作节奏：等待放量企稳信号，避免在情绪拐点盲目抄底。")
    else:
        suggestion.append("- 仓位建议：维持中性仓位，按计划执行分批交易。")
        suggestion.append("- 操作节奏：围绕主线进行低吸高抛，减少追涨频次。")

    suggestion.append("- 风控纪律：单笔设置止损，单一标的避免重仓。")
    return suggestion


def write_raw_capture(
    today: str,
    indices: list[IndexPoint],
    northbound: dict[str, float | None],
    errors: list[str],
    news_hints: list[str],
) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out = RAW_DIR / f"{today}-news.md"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    index_lines = []
    for idx in indices:
        index_lines.append(
            {
                "name": idx.name,
                "latest": idx.latest,
                "pct": idx.pct,
                "change": idx.change,
                "amount": idx.amount,
            }
        )

    body = [
        f"# A股原始采集 - {today}",
        "",
        f"- 采集时间：{now_str}",
        "- 数据源：Eastmoney 开放接口 + daily_news",
        "",
        "## 指数原始数据",
        "```json",
        json.dumps(index_lines, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 北向资金原始数据",
        "```json",
        json.dumps(northbound, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 当日新闻线索（来自 daily_news）",
        *news_hints,
        "",
        "## 采集异常",
    ]
    if errors:
        body.extend([f"- {err}" for err in errors])
    else:
        body.append("- 无")

    out.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")
    return out


def build_report(
    today: str,
    indices: list[IndexPoint],
    northbound: dict[str, float | None],
    errors: list[str],
) -> str:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    news_hints = load_news_hint(today)
    market = "\n".join(format_market_summary(indices, northbound))
    actions = "\n".join(build_action_suggestions(indices, northbound))
    risk_line = "- 数据抓取存在部分失败，请在实盘前二次确认关键指标。"
    if not errors:
        risk_line = "- 自动采集正常完成，仍需结合盘中量价变化动态调整。"

    # 自选基金分析
    self_selected_funds = load_self_selected_funds()
    self_selected = "\n".join(build_self_selected_section(self_selected_funds))

    return f"""# A股投资建议 - {today}

## 📊 市场整体判断
{market}
- 结论：先看指数共振与资金方向，再决定进攻还是防守节奏。

## 🎯 重点关注板块
- 科技成长（AI、半导体、软件）仍是核心观察主线，优先看成交额与龙头强度。
- 若主线强度不足，防守方向可关注宽基 ETF 与高股息品种的承接表现。

## 💹 具体操作建议
{actions}

## ⚠️ 风险提示
- 宏观与政策风险：监管口径、外围市场与汇率波动可能影响风险偏好。
- 交易风险：若出现放量下跌或高开低走，优先执行减仓和风控纪律。
{risk_line}

## 📈 自选基金分析
{self_selected}

## 📰 当日新闻线索（来自 daily_news）
{chr(10).join(news_hints)}

---
数据来源：Eastmoney 开放接口、daily_news、investing.md  
分析时间：{now_str}  
*免责声明：以上内容仅供参考，不构成投资建议。投资有风险，入市需谨慎。*
"""


def update_reports_json(today: str, content: str) -> None:
    """将当日日报内容追加到 public/reports.json，供前端页面读取。"""
    reports_json_path = REPO_ROOT / "public" / "reports.json"
    data: dict = {"reports": [], "data": {}}
    if reports_json_path.is_file():
        try:
            data = json.loads(reports_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    reports_list: list[str] = data.get("reports", [])
    data_map: dict[str, str] = data.get("data", {})

    data_map[today] = content
    if today not in reports_list:
        reports_list.insert(0, today)

    data["reports"] = reports_list
    data["data"] = data_map
    reports_json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Updated reports.json with {today}")


def main() -> None:
    today = datetime.date.today().isoformat()
    force = os.getenv("INVESTMENT_FORCE", "0") == "1"
    INVESTMENT_DIR.mkdir(parents=True, exist_ok=True)

    indices, err_indices = fetch_index_snapshot()
    northbound, err_northbound = fetch_northbound_flow()
    errors = [msg for msg in [err_indices, err_northbound] if msg]
    raw_path = write_raw_capture(today, indices, northbound, errors, load_news_hint(today))

    output_path = INVESTMENT_DIR / f"{today}.md"
    if output_path.exists() and not force:
        print(f"Skip: already exists -> {output_path}")
        print(f"Raw capture refreshed -> {raw_path}")
        return

    output_path.write_text(
        build_report(today, indices, northbound, errors),
        encoding="utf-8",
    )

    # 同步更新 public/reports.json，供前端页面展示
    update_reports_json(today, output_path.read_text(encoding="utf-8"))

    print(f"Generated: {output_path}")
    print(f"Raw capture: {raw_path}")


if __name__ == "__main__":
    main()
