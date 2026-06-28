"""
周报生成器 - 每周日运行

从 history.yaml 读取最近 7 天的记录，调用 AI 生成周报
"""

import argparse
import sys
import logging
from datetime import date, timedelta
from pathlib import Path

from cpsc_monitor.config import load_config
from cpsc_monitor.history import get_recent_runs
from cpsc_monitor.utils import setup_logging, ensure_dirs
from cpsc_monitor.ai_analyzer import _call_ai, _extract_json


WEEKLY_PROMPT = """你是亚马逊合规顾问。基于以下本周 7 天的运行记录，生成周报。

【本周记录】
{weekly_records}

【输出 Markdown 格式，不要 JSON 包装】

# CPSC 合规周报 - {week_range}

## 本周核心数据
- 公告总数：{total}
- 高风险 SKU 命中：{high_total}
- 节省潜在损失：约 ¥{saved_rmb} 万（粗略估算，每个高风险按 5 万算）

## 本周 Top 3 风险事件
（从本周高风险事件中挑 3 个最重要的）

## 下周预测
（基于本周趋势）

## 行动建议
- 立即：...
- 本周内：...
- 本月内：...
"""


def generate_weekly_report(target_week_end: date = None) -> str:
    """生成周报"""
    if target_week_end is None:
        target_week_end = date.today()

    # 取最近 7 天的记录
    runs = get_recent_runs(days=7)
    week_start = target_week_end - timedelta(days=6)

    logger = logging.getLogger("cpsc-monitor.weekly")
    logger.info(f"读取最近 7 天记录：{len(runs)} 条")

    # 统计数据
    total_announcements = sum(r.get("announcement_count", 0) for r in runs)
    high_total = sum(r.get("high", 0) for r in runs)
    saved_rmb = high_total * 5  # 粗略估算

    # 准备 prompt
    weekly_records_str = "\n".join(
        f"- {r.get('date', '')}: {r.get('announcement_count', 0)} 公告, "
        f"{r.get('high', 0)} 高风险, {r.get('medium', 0)} 中风险"
        for r in runs
    )

    prompt = WEEKLY_PROMPT.format(
        weekly_records=weekly_records_str or "本周无运行记录",
        week_range=f"{week_start.isoformat()} 至 {target_week_end.isoformat()}",
        total=total_announcements,
        high_total=high_total,
        saved_rmb=saved_rmb,
    )

    try:
        config = load_config()
        report = _call_ai(prompt, config)
    except Exception as e:
        logger.error(f"AI 生成周报失败：{e}，使用本地模板")
        report = _fallback_report(week_start, target_week_end, total_announcements, high_total, saved_rmb, runs)

    # 保存
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / f"{target_week_end.isoformat()}-weekly-report.md"
    report_file.write_text(report, encoding="utf-8")
    logger.info(f"周报已保存：{report_file}")

    return report


def _fallback_report(week_start, week_end, total, high_total, saved_rmb, runs):
    """降级周报模板（AI 失败时用）"""
    return f"""# CPSC 合规周报 - {week_start} 至 {week_end}

## 本周核心数据

| 指标 | 数值 |
|---|---|
| 公告总数 | {total} |
| 高风险 SKU 命中 | {high_total} |
| 节省潜在损失 | ¥{saved_rmb} 万（估算） |
| 实际运行天数 | {len(runs)} |

## 每日记录

{chr(10).join(f"- **{r.get('date')}**: {r.get('announcement_count', 0)} 公告, {r.get('high', 0)} 高风险" for r in runs)}

## 备注

AI 周报生成失败，使用本地降级模板。请检查 AI API 配置。

---

*由 CPSC 监控 Skill 自动生成（降级模式）*"""


def main():
    parser = argparse.ArgumentParser(description="CPSC 周报生成器")
    parser.add_argument("--date", type=str, help="指定周结束日期 YYYY-MM-DD（默认今天）")
    args = parser.parse_args()

    setup_logging()
    ensure_dirs(["logs", "output"])

    if args.date:
        from datetime import datetime
        target = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        target = date.today()

    generate_weekly_report(target)


if __name__ == "__main__":
    main()