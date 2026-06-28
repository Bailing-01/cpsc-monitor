"""
CPSC 监控 Skill - 主入口

每天早上 9 点自动跑一次（或手动触发）：
1. 加载 config.yaml
2. 抓取 CPSC 最新公告
3. AI 风险判断
4. 聚合分析
5. 生成报告 + 发邮件/短信
6. 更新历史

用法：
    python run.py                  # 用今天的日期跑
    python run.py --now           # 立刻跑（不等定时）
    python run.py --date 2026-06-28  # 跑指定日期
    python run.py --fetch-only    # 只抓取不分析（debug）
    python run.py --analyze-only  # 只分析不发送（debug）
    python run.py --no-send       # 跑全流程但不发送邮件/短信
"""

import argparse
import sys
import logging
from datetime import datetime, date
from pathlib import Path

from cpsc_monitor.config import load_config
from cpsc_monitor.fetcher import fetch_announcements
from cpsc_monitor.ai_analyzer import analyze_risks, summarize_announcements
from cpsc_monitor.report import render_report, send_email_alert, send_sms_alert
from cpsc_monitor.history import update_history, log_run
from cpsc_monitor.utils import setup_logging, ensure_dirs


def parse_args():
    parser = argparse.ArgumentParser(description="CPSC 监控 Skill 主程序")
    parser.add_argument("--now", action="store_true", help="立刻跑（默认等定时）")
    parser.add_argument("--date", type=str, help="指定日期 YYYY-MM-DD（默认今天）")
    parser.add_argument("--fetch-only", action="store_true", help="只抓取不分析")
    parser.add_argument("--analyze-only", action="store_true", help="只分析不发送")
    parser.add_argument("--no-send", action="store_true", help="跳过邮件/短信发送")
    return parser.parse_args()


def run(target_date: date, fetch_only=False, analyze_only=False, send_enabled=True):
    """
    主运行流程

    Args:
        target_date: 目标日期
        fetch_only: 只抓取公告，不做风险分析
        analyze_only: 只分析，不发送邮件/短信（覆盖 send_enabled）
        send_enabled: 是否启用邮件/短信发送
    """
    logger = logging.getLogger("cpsc-monitor")

    try:
        # Step 1: 加载配置
        logger.info(f"[1/6] 加载配置...")
        config = load_config()
        logger.info(f"  配置加载成功：{len(config['my_skus'])} 个 SKU，{len(config['alert_emails'])} 个告警邮箱")

        # Step 2: 抓取公告
        logger.info(f"[2/6] 抓取 CPSC 公告...")
        announcements = fetch_announcements(config, target_date)
        logger.info(f"  抓取到 {len(announcements)} 条公告")

        if fetch_only:
            logger.info("  --fetch-only 模式，跳过分析")
            return {"status": "ok", "announcement_count": len(announcements)}

        if not announcements:
            logger.warning("  今日无公告，跳过后续步骤")
            update_history(target_date, {"announcement_count": 0, "high": 0, "medium": 0, "low": 0})
            return {"status": "ok", "announcement_count": 0}

        # Step 3: AI 风险判断
        logger.info(f"[3/6] AI 风险判断...")
        risk_analysis = analyze_risks(announcements, config)
        high_count = sum(1 for r in risk_analysis if r.get("risk_level") == "high")
        medium_count = sum(1 for r in risk_analysis if r.get("risk_level") == "medium")
        low_count = sum(1 for r in risk_analysis if r.get("risk_level") == "low")
        logger.info(f"  高风险 {high_count} 个，中风险 {medium_count} 个，低风险 {low_count} 个")

        # Step 4: 聚合分析
        logger.info(f"[4/6] 聚合分析...")
        summary = summarize_announcements(announcements, risk_analysis, config)
        logger.info(f"  今日主题：{summary.get('todays_themes', [])}")

        # Step 5: 生成报告 + 发送
        logger.info(f"[5/6] 生成报告 + 发送告警...")
        report = render_report(target_date, risk_analysis, summary, config)
        report_path = Path(config["output"]["dir"]) / f"{target_date.isoformat()}-risk-report.md"
        report_path.write_text(report, encoding="utf-8")
        logger.info(f"  报告已保存：{report_path}")

        # 发送告警（除非 analyze-only 或 no-send）
        if analyze_only or not send_enabled:
            logger.info("  --no-send / --analyze-only 模式，跳过发送")
        elif high_count > 0:
            # 高风险 → 发邮件
            send_email_alert(config, report, target_date)
            logger.info(f"  邮件已发送到：{config['alert_emails']}")
            # 高风险 → 发短信（如果启用）
            if config.get("sms", {}).get("enabled"):
                send_sms_alert(config, risk_analysis, target_date)
                logger.info(f"  短信已发送：{config['sms']['phone']}")
        else:
            logger.info("  无高风险，跳过邮件/短信发送")

        # Step 6: 更新历史
        logger.info(f"[6/6] 更新历史记录...")
        update_history(target_date, {
            "announcement_count": len(announcements),
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
            "themes": summary.get("todays_themes", []),
        })

        logger.info(f"✅ 运行完成 - {target_date}")
        return {
            "status": "ok",
            "announcement_count": len(announcements),
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
        }

    except FileNotFoundError as e:
        logger.error(f"❌ 配置文件缺失：{e}")
        logger.error("  请先复制 config.example.yaml 为 config.yaml 并填写")
        sys.exit(1)
    except AssertionError as e:
        logger.error(f"❌ 配置校验失败：{e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"❌ 运行失败：{e}")
        # 故障兜底：邮件告警（如果有配置）
        try:
            config = load_config()
            send_email_alert(
                config,
                f"CPSC 监控 Skill 运行失败\n\n时间：{datetime.now()}\n错误：{e}\n\n请检查 logs/cron.log",
                target_date,
                subject_prefix="❌ [Skill 故障]",
            )
        except Exception:
            pass  # 邮件发送也失败就算了
        sys.exit(1)


def main():
    args = parse_args()
    setup_logging()
    ensure_dirs(["logs", "output"])
    log_run()

    # 确定目标日期
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"日期格式错误：{args.date}（应为 YYYY-MM-DD）")
            sys.exit(1)
    else:
        target_date = date.today()

    run(
        target_date=target_date,
        fetch_only=args.fetch_only,
        analyze_only=args.analyze_only,
        send_enabled=not args.no_send,
    )


if __name__ == "__main__":
    main()