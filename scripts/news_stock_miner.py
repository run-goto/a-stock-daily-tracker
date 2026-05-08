"""
新闻监控 → 题材挖掘 → A股候选股票映射

目标：
1. 抓取热门财经新闻/快讯；
2. 识别新闻中的主题词；
3. 映射到 A 股题材方向；
4. 给出可能受益的候选股票；
5. 输出 DataFrame，供 daily_report.py 合并到日报。

说明：
- 新闻接口优先使用 AkShare；
- 若某个第三方接口失效，脚本会跳过并继续执行；
- 股票映射表是规则型起步版本，后续可以逐步扩展成行业/概念库。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List

import pandas as pd

try:
    import akshare as ak
except Exception:  # pragma: no cover
    ak = None


@dataclass
class ThemeRule:
    theme: str
    keywords: List[str]
    stocks: List[Dict[str, str]]
    note: str


THEME_RULES: List[ThemeRule] = [
    ThemeRule(
        theme="AI算力 / 国产算力",
        keywords=["算力", "AI服务器", "数据中心", "国产CPU", "GPU", "昇腾", "华为算力", "液冷"],
        stocks=[
            {"code": "000066", "name": "中国长城"},
            {"code": "000818", "name": "航锦科技"},
            {"code": "600673", "name": "东阳光"},
            {"code": "000889", "name": "中嘉博创"},
        ],
        note="AI硬件核心",
    ),
    ThemeRule(
        theme="光通信 / CPO / 光模块",
        keywords=["CPO", "光模块", "光通信", "光芯片", "光纤", "800G", "1.6T"],
        stocks=[
            {"code": "002281", "name": "光迅科技"},
            {"code": "600522", "name": "中天科技"},
            {"code": "002491", "name": "通鼎互联"},
            {"code": "688167", "name": "炬光科技"},
            {"code": "688313", "name": "仕佳光子"},
            {"code": "603618", "name": "杭电股份"},
        ],
        note="光通信强势",
    ),
    ThemeRule(
        theme="PCB / CCL / 电子布",
        keywords=["PCB", "覆铜板", "CCL", "电子布", "玻纤", "高速铜箔", "HDI"],
        stocks=[
            {"code": "002384", "name": "东山精密"},
            {"code": "002436", "name": "兴森科技"},
            {"code": "601208", "name": "东材科技"},
            {"code": "603256", "name": "宏和科技"},
            {"code": "605258", "name": "协和电子"},
            {"code": "605006", "name": "山东玻纤"},
        ],
        note="PCB主线",
    ),
    ThemeRule(
        theme="半导体 / 先进封装 / 存储",
        keywords=["半导体", "先进封装", "HBM", "存储", "SSD", "晶圆", "芯片"],
        stocks=[
            {"code": "688584", "name": "盛合晶微"},
            {"code": "688496", "name": "大普微-UW"},
            {"code": "002436", "name": "兴森科技"},
            {"code": "000066", "name": "中国长城"},
        ],
        note="半导体弹性",
    ),
    ThemeRule(
        theme="电力 / 算电协同",
        keywords=["电力", "绿电", "虚拟电厂", "算电协同", "储能", "特高压"],
        stocks=[
            {"code": "600396", "name": "华电辽能"},
            {"code": "601991", "name": "大唐发电"},
            {"code": "600719", "name": "大连热电"},
        ],
        note="电力活跃",
    ),
    ThemeRule(
        theme="AI应用 / 营销",
        keywords=["AI应用", "AI营销", "智能体", "Agent", "广告投放", "短视频生成"],
        stocks=[
            {"code": "301171", "name": "易点天下"},
        ],
        note="AI应用端",
    ),
]


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def fetch_news(limit: int = 200) -> pd.DataFrame:
    """抓取新闻。优先使用 AkShare，失败时返回空表。"""
    frames: List[pd.DataFrame] = []

    if ak is None:
        return pd.DataFrame(columns=["datetime", "title", "content", "source"])

    # 财联社快讯：AkShare 旧接口 stock_telegraph_cls 已更名为 stock_info_global_cls
    for func_name, source in [
        ("stock_info_global_cls", "财联社"),
        ("stock_info_global_em", "东方财富快讯"),
        ("stock_info_global_sina", "新浪财经快讯"),
    ]:
        try:
            func = getattr(ak, func_name)
            df = func()
            if df is None or df.empty:
                continue
            df = df.copy()
            df["source"] = source
            frames.append(df)
        except Exception as exc:
            print(f"[WARN] fetch {func_name} failed: {exc}")

    if not frames:
        return pd.DataFrame(columns=["datetime", "title", "content", "source"])

    raw = pd.concat(frames, ignore_index=True)

    # 兼容不同接口字段名
    title_col = next((c for c in ["标题", "title", "内容", "摘要"] if c in raw.columns), None)
    time_col = next((c for c in ["时间", "datetime", "发布时间", "日期"] if c in raw.columns), None)
    content_col = next((c for c in ["内容", "摘要", "title", "标题"] if c in raw.columns), None)

    result = pd.DataFrame()
    result["datetime"] = raw[time_col] if time_col else ""
    result["title"] = raw[title_col].map(normalize_text) if title_col else ""
    result["content"] = raw[content_col].map(normalize_text) if content_col else result["title"]
    result["source"] = raw.get("source", "")
    result = result.drop_duplicates(subset=["title", "content"]).head(limit)
    return result


def match_themes(news_df: pd.DataFrame) -> pd.DataFrame:
    """新闻 → 题材 → 候选股票。"""
    rows: List[Dict[str, object]] = []
    if news_df.empty:
        return pd.DataFrame(columns=["theme", "code", "name", "matched_keywords", "news_count", "source_titles", "note"])

    news_df = news_df.copy()
    news_df["merged_text"] = (news_df["title"].fillna("") + " " + news_df["content"].fillna(""))

    for rule in THEME_RULES:
        pattern = "|".join(re.escape(k) for k in rule.keywords)
        matched = news_df[news_df["merged_text"].str.contains(pattern, case=False, na=False)]
        if matched.empty:
            continue

        matched_keywords = sorted({kw for kw in rule.keywords if matched["merged_text"].str.contains(re.escape(kw), case=False, na=False).any()})
        titles = matched["title"].dropna().astype(str).head(3).tolist()

        for stock in rule.stocks:
            rows.append(
                {
                    "theme": rule.theme,
                    "code": stock["code"],
                    "name": stock["name"],
                    "matched_keywords": "/".join(matched_keywords),
                    "news_count": int(len(matched)),
                    "source_titles": " | ".join(titles),
                    "note": rule.note,
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.sort_values(["news_count", "theme"], ascending=[False, True]).drop_duplicates(subset=["code"])
    return df.reset_index(drop=True)


def mine_news_stocks(limit: int = 200) -> pd.DataFrame:
    news = fetch_news(limit=limit)
    return match_themes(news)


if __name__ == "__main__":
    result = mine_news_stocks()
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"news stock candidates: {today}")
    print(result.to_markdown(index=False))
