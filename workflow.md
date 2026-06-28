# 工作流 + 报告模板

> ⚠️ 设计稿，最终版拆成 3 个文件分别拷到 GitHub 仓库

---

# 一、workflow.md（每日工作流说明）

```markdown
# CPSC 监控 Skill 工作流

## 每日定时任务（cron）

```bash
# 每天早上 9:00 执行
0 9 * * * cd /path/to/cpsc-monitor && python run.py >> ./logs/cron.log 2>&1
```

## run.py 执行步骤

### Step 1: 加载配置（5 秒）
```python
import yaml
config = yaml.safe_load(open("config.yaml"))
assert len(config["my_skus"]) >= 10, "至少填 10 个 SKU"
```

### Step 2: 抓取公告（30 秒）
```python
# 抓取 3 个 source
for source in config["sources"]:
    fetch(source)
# 结果存到 output/{date}-raw-announcements.md
```

### Step 3: AI 风险判断（1-3 分钟）
```python
# 对每条公告调 Prompt 1
for announcement in announcements:
    risk = call_ai(Prompt_1, announcement, config["my_skus"])
# 结果存到 output/{date}-risk-analysis.json
```

### Step 4: 聚合分析（30 秒）
```python
# 调 Prompt 2
summary = call_ai(Prompt_2, announcements, config["my_skus"])
# 结果存到 output/{date}-summary.json
```

### Step 5: 生成报告 + 发邮件（10 秒）
```python
# 渲染 risk-report.md
report = render_template("templates/risk-report.md", risk_analysis, summary)
save_to_file(f"output/{date}-risk-report.md", report)

# 发邮件
if any(risk["risk_level"] == "high" for risk in risks):
    send_email(config["alert_emails"], report)
    if config["sms"]["enabled"]:
        send_sms(config["sms"]["phone"], alert_sms_template(risk))
```

### Step 6: 更新历史（5 秒）
```python
# 更新 history.yaml
update_history(date, summary_stats)
```

### 故障处理
- Step 2 失败 → 重试 3 次，仍失败跳过当日 + 邮件告警
- Step 3 失败 → 用本地缓存的 prompt 重试 1 次，仍失败跳过
- Step 5 失败 → 保留本地报告，下次补发

## 手动运行

```bash
# 立即跑一次（不等定时）
python run.py --now

# 跑指定日期
python run.py --date 2026-06-28

# 只抓取不分析（debug 用）
python run.py --fetch-only

# 只分析不发送（debug 用）
python run.py --analyze-only --no-send
```

## 周报（每周日）

```bash
# 每周日 20:00 自动跑
0 20 * * 0 cd /path/to/cpsc-monitor && python weekly.py >> ./logs/weekly.log 2>&1
```
```

---

# 二、templates/risk-report.md

```markdown
# CPSC 合规日报 - {date}

> 生成时间：{generated_at}
> 抓取公告数：{announcement_count}
> 命中 SKU 数：{matched_sku_count}

---

## ⚠️ 今日高风险（必须立刻处理）

{red_box_start}
**{high_risk_count} 个高风险 SKU 需要你在 14 天内提交报告**
{red_box_end}

{h_for_each_high_risk_sku}
### 🔴 {sku_name} (ASIN: {asin})
- **风险等级**：HIGH
- **风险描述**：{specific_risk}
- **公告来源**：[{title}]({source_url})
- **截止日期**：{deadline_date}（还剩 {days_left} 天）

**7 天行动方案**：
- **Day 1-2**：
  - {action_1}
  - {action_2}
- **Day 3-5**：
  - {action_3}
  - {action_4}
- **Day 6-7**：
  - {action_5}
  - {action_6}

**预估成本**：${estimated_cost_usd}
**不做的后果**：{consequence}

---
{end_for_each}

## 🟡 今日中风险（本周内处理）

{m_for_each_medium_risk_sku}
### 🟡 {sku_name}
- **风险等级**：MEDIUM
- **风险描述**：{specific_risk}
- **建议动作**：{action}

---
{end_for_each}

## 🟢 今日新增公告（仅供参考）

{l_for_each_low_risk_sku}
- [{title}]({url}) - {published_date}
{end_for_each}

## 本周趋势

**主题**：{todays_themes}
**累计 7 天反复出现品类**：{recurring_categories_7d}
**下周预测**：{next_week_prediction}

---

## 数据统计

| 指标 | 数值 |
|---|---|
| 抓取公告总数 | {total} |
| 命中 SKU 总数 | {matched} |
| 高风险 | {high} |
| 中风险 | {medium} |
| 低风险 | {low} |
| 本周累计高风险 | {week_high_total} |
| 本月累计高风险 | {month_high_total} |

---

*本报告由 CPSC 监控 Skill 自动生成。*
*问题反馈：微信公众号"Bailing 跨境"留言。*
```

---

# 三、templates/alert-sms.md

```markdown
🔴 CPSC 高风险告警

{sku_name} ({asin})
风险：{specific_risk_short}
截止：{deadline_date}
详情：见邮件
```

---

# 四、templates/alert-email.md（邮件正文 HTML）

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: -apple-system, sans-serif; line-height: 1.6; color: #1a1a1a; }
    .header { background: #dc2626; color: white; padding: 16px; border-radius: 8px; }
    .sku { background: #fef2f2; border-left: 4px solid #dc2626; padding: 16px; margin: 16px 0; }
    .action { background: #f0f9ff; padding: 12px; border-radius: 4px; margin: 8px 0; }
    .footer { color: #666; font-size: 12px; margin-top: 24px; }
  </style>
</head>
<body>
  <div class="header">
    <h2>⚠️ CPSC 高风险告警 - {date}</h2>
    <p>{high_risk_count} 个 SKU 需要立刻处理</p>
  </div>

  {for_each_high_risk_sku}
  <div class="sku">
    <h3>🔴 {sku_name} (ASIN: {asin})</h3>
    <p><strong>风险：</strong>{specific_risk}</p>
    <p><strong>截止：</strong>{deadline_date}（还剩 {days_left} 天）</p>
    <div class="action">
      <strong>立刻行动：</strong>
      <ol>
        <li>{action_1}</li>
        <li>{action_2}</li>
        <li>{action_3}</li>
      </ol>
    </div>
    <p><a href="{full_report_link}">查看完整报告 →</a></p>
  </div>
  {end_for_each}

  <div class="footer">
    <p>本邮件由 CPSC 监控 Skill 自动发送</p>
    <p>完整报告：<a href="{full_report_link}">{full_report_link}</a></p>
    <p>取消订阅：回复"unsubscribe"</p>
  </div>
</body>
</html>
```

---

# 五、templates/weekly-report.md（周报）

```markdown
# CPSC 合规周报 - {week_range}

## 本周核心数据

| 指标 | 数值 |
|---|---|
| 公告总数 | {total_announcements} |
| 高风险 SKU 命中 | {high_count} |
| 已提交报告 | {submitted_count} |
| 节省潜在损失 | ¥{saved_rmb} 万 |

## 本周 Top 3 风险事件

### 🥇 {event_1_title}
- 影响 SKU：{event_1_skus}
- 应对动作：{event_1_actions}
- 当前状态：{event_1_status}

### 🥈 {event_2_title}
...

### 🥉 {event_3_title}
...

## 下周预测

基于本周趋势，**下周 CPSC 可能重点关注**：
- {prediction_1}
- {prediction_2}

## 行动建议

### 立即（24 小时内）
- {urgent_action_1}
- {urgent_action_2}

### 本周内
- {week_action_1}

### 本月内
- {month_action_1}

---

*由 CPSC 监控 Skill 自动生成 | 公众号"Bailing 跨境"*
```

---

# 六、设计说明（这一段不放到模板里）

## 模板的 3 个核心设计原则

1. **分级突出颜色**
   - HIGH = 红色（必须立刻处理）
   - MEDIUM = 黄色（本周内处理）
   - LOW = 绿色（仅供参考）

2. **截止日期永远高亮**
   - 任何 14 天提交窗口的 SKU，必须在报告顶部红字提醒
   - 邮件和短信都单独强调"截止日期 + 还剩几天"

3. **action 必须可执行**
   - 不给"建议尽快处理"这种空话
   - 每个 action 以动词开头（联系、提交、准备、检查）
   - 7 天内分阶段（Day 1-2 / 3-5 / 6-7）

## 模板为什么用 Markdown 而不是纯 HTML？

- Markdown 在公众号、邮件、GitHub 三端都能渲染
- HTML 只用在邮件（HTML 邮件）
- 周报用 Markdown，方便用户转 PDF / 印出来贴墙

## 模板测试方法

拿一个真实的 CPSC 召回事件（最近一周的），手动填到模板里：
1. 看渲染效果（HTML 邮件在 Gmail/Outlook 是否正常）
2. 看 markdown 在公众号编辑器是否正常
3. 看 SMS 字符数（必须 ≤ 70 字）

3 个端都对，模板才算调好。