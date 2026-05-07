# A股每日异动股票跟踪

用于每天保存 A 股异动股票清单，包括连续涨停、成交量放大、热门强势股，以及买入分析结论。

## 目录结构

```text
reports/        # Markdown 日报
data/           # CSV / JSON 结构化数据
scripts/        # AkShare 数据采集脚本
requirements.txt
```

## 输出字段

| 字段 | 说明 |
|---|---|
| 类型 | 连续涨停 / 成交量放大 / 热门强势股 |
| 代码 | A股股票代码 |
| 名称 | 股票名称 |
| 所属方向/题材 | 当日主要题材归因 |
| 今日涨跌幅 | 当日涨跌幅 |
| 成交额 | 当日成交额 |
| 是否涨停 | 是 / 否 |
| 连板天数 | 连续涨停天数 |
| 买入分析 | 简短判断过程 |
| 买入结论 | 可小仓试错 / 回调关注 / 只观察 / 不追高 / 规避 |
| 备注 | 短句备注 |

## 数据文件

- `reports/YYYY-MM-DD.md`：每日 Markdown 表格
- `data/YYYY-MM-DD.csv`：每日 CSV 数据
- `data/YYYY-MM-DD.json`：每日 JSON 数据

## 本地运行

```bash
pip install -r requirements.txt
python scripts/daily_report.py
```
