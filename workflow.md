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

## 实现说明

`run.py` 的实际实现见同目录的 `run.py` 和 `cpsc_monitor/` 模块：

- `cpsc_monitor/config.py` — 配置加载和验证
- `cpsc_monitor/fetcher.py` — CPSC 公告抓取（RSS + SaferProducts）
- `cpsc_monitor/ai_analyzer.py` — AI 风险判断（调 Anthropic/OpenAI）
- `cpsc_monitor/report.py` — 报告渲染 + 邮件发送
- `cpsc_monitor/history.py` — 历史记录管理
- `cpsc_monitor/utils.py` — 工具函数（重试/日志/时间）