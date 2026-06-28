# CPSC 合规日报 - {date}

> 生成时间：{generated_at}
> 抓取公告数：{announcement_count}
> 命中 SKU 数：{matched_sku_count}

---

## ⚠️ 今日高风险（必须立刻处理）

> **{high_risk_count} 个高风险 SKU 需要你在 14 天内提交报告**

{for each high_risk_sku}
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
{end for}

## 🟡 今日中风险（本周内处理）

{for each medium_risk_sku}
### 🟡 {sku_name}
- **风险等级**：MEDIUM
- **风险描述**：{specific_risk}
- **建议动作**：{action}

---
{end for}

## 🟢 今日新增公告（仅供参考）

{for each low_risk_sku}
- [{title}]({url}) - {published_date}
{end for}

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