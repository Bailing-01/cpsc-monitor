"""
报告生成 + 邮件 / 短信发送
"""

import logging
import smtplib
from datetime import date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import List, Dict, Any
import os

logger = logging.getLogger("cpsc-monitor.report")


def render_report(target_date: date, risk_analysis: List[Dict[str, Any]], summary: Dict[str, Any], config: dict) -> str:
    """
    渲染 risk-report.md 模板

    Returns:
        完整的 Markdown 报告字符串
    """
    template_path = Path(__file__).parent.parent / "templates" / "risk-report.md"
    template = template_path.read_text(encoding="utf-8")

    # 按风险等级分组
    high_risks = [r for r in risk_analysis if r.get("risk_level") == "high"]
    medium_risks = [r for r in risk_analysis if r.get("risk_level") == "medium"]
    low_risks = [r for r in risk_analysis if r.get("risk_level") == "low"]

    # 替换基本变量
    output = template.replace("{date}", target_date.isoformat())
    output = output.replace("{generated_at}", target_date.isoformat())
    output = output.replace("{announcement_count}", str(len(risk_analysis)))
    output = output.replace("{matched_sku_count}", str(sum(len(r.get("matched_skus", [])) for r in risk_analysis)))
    output = output.replace("{high_risk_count}", str(len(high_risks)))

    # 高风险 SKU 区块
    high_section = ""
    for risk in high_risks:
        for sku in risk.get("matched_skus", []):
            ann = risk.get("_announcement", {})
            actions = risk.get("action_required", [])
            deadline = target_date + timedelta(days=risk.get("deadline_days", 14))
            days_left = (deadline - target_date).days

            # 分配 action 到 7 天
            day1_2 = actions[:2] if len(actions) >= 2 else actions
            day3_5 = actions[2:4] if len(actions) >= 4 else actions[2:]
            day6_7 = actions[4:] if len(actions) > 4 else []

            high_section += f"### 🔴 {sku.get('sku_name', 'Unknown')} (ASIN: {sku.get('asin', 'N/A')})\n\n"
            high_section += f"- **风险等级**：HIGH\n"
            high_section += f"- **风险描述**：{sku.get('specific_risk', risk.get('risk_rationale', ''))}\n"
            high_section += f"- **公告来源**：[{ann.get('title', '')}]({risk.get('source_url', '#')})\n"
            high_section += f"- **截止日期**：{deadline.isoformat()}（还剩 {days_left} 天）\n\n"
            high_section += "**7 天行动方案**：\n"
            high_section += "- **Day 1-2**：\n"
            for a in day1_2:
                high_section += f"  - {a}\n"
            high_section += "- **Day 3-5**：\n"
            for a in day3_5:
                high_section += f"  - {a}\n"
            high_section += "- **Day 6-7**：\n"
            for a in day6_7:
                high_section += f"  - {a}\n"
            high_section += f"\n**预估成本**：${risk.get('estimated_cost_usd', 0)}\n"
            high_section += f"**不做的后果**：Listing 下架 + 资金冻结 + 最高 10 万美元罚款\n\n---\n\n"

    # 高风险块替换（找 for 块标记替换）
    output = _replace_for_block(output, "high_risk_sku", high_section)
    output = output.replace("{high_risk_count}", str(len(high_risks)))

    # 中风险块
    medium_section = ""
    for risk in medium_risks:
        for sku in risk.get("matched_skus", []):
            medium_section += f"### 🟡 {sku.get('sku_name', 'Unknown')}\n\n"
            medium_section += f"- **风险等级**：MEDIUM\n"
            medium_section += f"- **风险描述**：{sku.get('specific_risk', '')}\n"
            medium_section += f"- **建议动作**：{'; '.join(risk.get('action_required', []))}\n\n---\n\n"

    output = _replace_for_block(output, "medium_risk_sku", medium_section)

    # 低风险块（公告列表）
    low_section = ""
    for risk in low_risks:
        ann = risk.get("_announcement", {})
        low_section += f"- [{ann.get('title', '')}]({risk.get('source_url', '#')}) - {ann.get('published', '')}\n"
    output = _replace_for_block(output, "low_risk_sku", low_section)

    # 统计和趋势
    output = output.replace("{total}", str(len(risk_analysis)))
    output = output.replace("{matched}", str(sum(len(r.get("matched_skus", [])) for r in risk_analysis)))
    output = output.replace("{high}", str(len(high_risks)))
    output = output.replace("{medium}", str(len(medium_risks)))
    output = output.replace("{low}", str(len(low_risks)))
    output = output.replace("{week_high_total}", str(len(high_risks)))  # 简化：本周=今日
    output = output.replace("{month_high_total}", str(len(high_risks)))
    output = output.replace("{todays_themes}", ", ".join(summary.get("todays_themes", [])) or "无明显主题")
    output = output.replace("{recurring_categories_7d}", ", ".join(summary.get("recurring_categories_7d", [])) or "暂无")
    output = output.replace("{next_week_prediction}", summary.get("next_week_prediction", "无预测"))

    return output


def _replace_for_block(template: str, block_name: str, replacement: str) -> str:
    """替换模板中的 {for each X}...{end for} 块"""
    import re
    pattern = rf"\{{for each {block_name}\}}.*?\{{end for\}}"
    if not re.search(pattern, template, re.DOTALL):
        # 没有 for 块，直接返回
        return template
    return re.sub(pattern, replacement, template, flags=re.DOTALL)


def send_email_alert(config: dict, report_content: str, target_date: date, subject_prefix: str = "⚠️ CPSC 合规日报"):
    """
    发送告警邮件

    使用环境变量配置的 SMTP：
    - SMTP_HOST
    - SMTP_PORT (默认 587)
    - SMTP_USER
    - SMTP_PASSWORD
    """
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    if not all([smtp_host, smtp_user, smtp_password]):
        logger.warning("  邮件未发送：SMTP 环境变量未配置（需要 SMTP_HOST/SMTP_USER/SMTP_PASSWORD）")
        return False

    subject = f"{subject_prefix} - {target_date.isoformat()}"

    # 给每个收件人发一封
    for recipient in config["alert_emails"]:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = recipient

            # 纯文本版本
            text_part = MIMEText(report_content, "plain", "utf-8")
            msg.attach(text_part)

            # 发送
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

            logger.info(f"  邮件已发送：{recipient}")
        except Exception as e:
            logger.error(f"  邮件发送失败 [{recipient}]：{e}")
            return False

    return True


def send_sms_alert(config: dict, risk_analysis: List[Dict[str, Any]], target_date: date):
    """发送高风险短信（Twilio）"""
    if not config.get("sms", {}).get("enabled"):
        return False

    try:
        from twilio.rest import Client
    except ImportError:
        logger.warning("  twilio 库未安装，跳过短信发送")
        return False

    account_sid = config["sms"].get("twilio_account_sid") or os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = config["sms"].get("twilio_auth_token") or os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = config["sms"].get("twilio_from_number") or os.environ.get("TWILIO_FROM_NUMBER")

    if not all([account_sid, auth_token, from_number]):
        logger.warning("  Twilio 配置不完整，跳过短信")
        return False

    # 找最高风险的 SKU
    high_risks = [r for r in risk_analysis if r.get("risk_level") == "high"]
    if not high_risks:
        return False

    first_risk = high_risks[0]
    matched_skus = first_risk.get("matched_skus", [])
    if not matched_skus:
        return False

    first_sku = matched_skus[0]
    deadline = target_date + timedelta(days=first_risk.get("deadline_days", 14))

    message_body = (
        f"🔴 CPSC 高风险告警\n"
        f"{first_sku.get('sku_name', '')} ({first_sku.get('asin', '')})\n"
        f"风险：{first_sku.get('specific_risk', '')[:30]}\n"
        f"截止：{deadline.isoformat()}\n"
        f"详情：见邮件"
    )

    # 截断到 70 字（SMS 单条上限）
    if len(message_body) > 70:
        message_body = message_body[:67] + "..."

    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=message_body,
            from_=from_number,
            to=config["sms"]["phone"],
        )
        logger.info(f"  短信已发送 SID: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"  短信发送失败：{e}")
        return False