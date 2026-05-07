"""
A股每日异动股票采集脚本。

功能：
1. 使用 AkShare 获取 A 股行情数据。
2. 识别涨停股、热门强势股，并预留成交量放大和连板统计扩展。
3. 输出 Markdown / CSV / JSON。

注意：题材归因、龙虎榜和买入分析建议后续接入新闻源、龙虎榜接口和自定义规则库。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import akshare as ak
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data"

COLUMNS = [
    "类型", "代码", "名称", "所属方向/题材", "今日涨跌幅", "成交额", "是否涨停",
    "连板天数", "买入分析", "买入结论", "备注"
]


def normalize_code(code: str) -> str:
    return str(code).zfill(6)


def is_limit_up(code: str, pct_chg: float) -> bool:
    code = normalize_code(code)
    if code.startswith(("300", "301", "688")):
        return pct_chg >= 19.8
    return pct_chg >= 9.8


def calc_buy_conclusion(theme: str, pct_text: str, limit_days: str) -> tuple[str, str]:
    try:
        days = int(limit_days) if limit_days != "—" else 0
    except ValueError:
        days = 0

    if days >= 2:
        return "连板后追高险", "不追高"
    if "20" in pct_text:
        return "20cm追高险", "不追高"
    if any(k in theme for k in ["AI", "算力", "光通信", "CPO", "PCB", "半导体"]):
        return "主线强等回调", "回调关注"
    return "热度高买点不清", "只观察"


def build_daily_rows() -> pd.DataFrame:
    spot = ak.stock_zh_a_spot_em()
    rows = []

    for _, row in spot.iterrows():
        code = normalize_code(row.get("代码", ""))
        name = row.get("名称", "")
        pct = float(row.get("涨跌幅", 0) or 0)
        amount = row.get("成交额", "—")

        if not is_limit_up(code, pct):
            continue

        theme = "待归因"
        pct_text = f"{pct:.2f}%"
        buy_analysis, buy_conclusion = calc_buy_conclusion(theme, pct_text, "—")
        rows.append({
            "类型": "热门强势股",
            "代码": code,
            "名称": name,
            "所属方向/题材": theme,
            "今日涨跌幅": pct_text,
            "成交额": amount,
            "是否涨停": "是",
            "连板天数": "—",
            "买入分析": buy_analysis,
            "买入结论": buy_conclusion,
            "备注": "涨停股",
        })

    if not rows:
        rows.append({c: "暂无" for c in COLUMNS})
        rows[0]["买入结论"] = "只观察"

    return pd.DataFrame(rows, columns=COLUMNS)


def save_outputs(df: pd.DataFrame, trade_date: str) -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)

    (REPORT_DIR / f"{trade_date}.md").write_text(
        f"# A股每日异动股票跟踪 - {trade_date}\n\n" + df.to_markdown(index=False) + "\n",
        encoding="utf-8",
    )
    df.to_csv(DATA_DIR / f"{trade_date}.csv", index=False, encoding="utf-8")
    (DATA_DIR / f"{trade_date}.json").write_text(
        json.dumps(df.to_dict(orient="records"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    trade_date = datetime.now().strftime("%Y-%m-%d")
    df = build_daily_rows()
    save_outputs(df, trade_date)


if __name__ == "__main__":
    main()
