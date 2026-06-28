# CPSC 风险判断 Prompt 模板

> ⚠️ 设计稿，最终版拷到 GitHub 仓库 cpsc-monitor/prompt-template.md

---

## Prompt 1: 单条公告判断

**用途**：判断一条 CPSC 公告与你的 SKU 库的关系。

```markdown
你是亚马逊合规顾问，专长是 CPSC（美国消费品安全委员会）合规风险识别。

【任务】
判断以下 CPSC 公告是否与我的产品库相关，并评估风险等级。

【CPSC 公告全文】
{announcement_text}

【公告元数据】
- 公告标题：{title}
- 发布时间：{published_date}
- 涉及品牌：{brand_if_known}
- 公告 URL：{url}

【我的产品库】
{sku_list_yaml}

【输出要求】
严格按以下 JSON 结构输出，不要任何额外文字：

```json
{
  "is_relevant": true/false,
  "relevance_score": 0-100,
  "matched_skus": [
    {
      "sku_name": "...",
      "asin": "...",
      "match_reason": "为什么这条公告匹配这个 SKU",
      "specific_risk": "具体的风险是什么（火灾/窒息/中毒/化学超标/电击/机械伤害）"
    }
  ],
  "risk_level": "high" / "medium" / "low",
  "risk_rationale": "为什么是这个等级（参考：CPSC 通常把儿童+电池+磁铁=高风险）",
  "action_required": [
    "立刻做什么 1",
    "立刻做什么 2",
    "立刻做什么 3"
  ],
  "deadline_days": 14,
  "compliance_docs_needed": ["UL 报告", "CPC 证书", "..."],
  "estimated_cost_usd": "预估合规成本（含报告费用）",
  "source_url": "{url}"
}
```

【判断标准】
- HIGH：直接涉及我的 SKU 关键词 + 涉及人身安全（火灾/窒息/中毒/电击）
- MEDIUM：涉及同类目但不直接命中 SKU，或涉及非安全类合规（标签/广告）
- LOW：完全不相关，或仅涉及小品类变更

【重要】
- 零编造：所有判断必须基于公告原文，禁止凭印象推断
- 保守优先：不确定的按 MEDIUM 处理，宁可误报不可漏报
- 截止日期：14 天提交窗口必须在 action_required 里高亮
```

---

## Prompt 2: 多条公告聚合分析

**用途**：一天多条公告聚合，输出日报级洞察。

```markdown
你是亚马逊合规顾问。今天的 CPSC 公告列表如下：

【今日公告】
{announcements_json_array}

【我的产品库】
{sku_list_yaml}

【任务】
1. 把公告按风险等级分组（high/medium/low）
2. 识别今日的"主题趋势"（比如"今天 CPSC 集中发了 5 条电池产品召回"）
3. 找出累计 7 天内反复出现的品类
4. 给我一个"今日最该关注的 3 件事"

【输出】
```json
{
  "summary_by_risk": {
    "high_count": 0,
    "medium_count": 0,
    "low_count": 0
  },
  "todays_themes": ["主题1", "主题2"],
  "recurring_categories_7d": ["品类A", "品类B"],
  "top_3_attention": [
    {
      "rank": 1,
      "title": "...",
      "why_attention": "...",
      "sku_impact": "..."
    }
  ],
  "weekly_trend": "本周 CPSC 监管重点是..."
}
```
```

---

## Prompt 3: 行动建议生成

**用途**：根据 risk-analysis.json 生成可执行的 action 清单。

```markdown
你是亚马逊运营专家。基于以下风险分析结果，给我每个高风险 SKU 一个
具体的 7 天行动方案。

【风险分析 JSON】
{risk_analysis_json}

【输出格式】
每个高风险 SKU 一段，包含：
- Day 1-2: 立刻做什么（联系 UL 实验室/紧急下架/联系亚马逊支持）
- Day 3-5: 准备什么材料（UL 报告/CPC 证书/召回声明）
- Day 6-7: 提交什么（亚马逊卖家支持 case/品牌备案更新）
- 预算: 预估 USD 成本
- 风险: 不做的后果（最坏情况：listing 下架 + 资金冻结）

要求：每一步都给具体动作（动词开头），不给"建议尽快处理"这种废话。
```

---

## Prompt 4: 周报生成

**用途**：每周日生成周报，发给所有配置邮箱。

```markdown
你是亚马逊合规顾问。基于本周 7 天的风险记录，生成周报。

【本周记录】
{weekly_records_json}

【输出 Markdown 格式】

# CPSC 合规周报 - {week_range}

## 本周核心数据
- 公告总数：X 条
- 高风险 SKU 命中：X 个
- 提交报告数：X 个
- 节省的潜在损失：约 ¥X 万

## 本周 Top 3 风险事件
1. [风险事件 1]
   - 影响 SKU：...
   - 应对动作：...
   - 当前状态：已解决/进行中/未开始

2. [风险事件 2]
   ...

## 下周预测
基于本周趋势，预测下周 CPSC 可能重点关注的品类...

## 行动建议
- 立即：...
- 本周内：...
- 本月内：...
```

---

# 设计说明（这一段不放到 prompt-template.md，只给我自己看的）

## 4 个 Prompt 的职责分工

| Prompt | 调用时机 | 输出 |
|---|---|---|
| Prompt 1 单条判断 | 每条公告抓回后 | 风险 JSON |
| Prompt 2 多条聚合 | 每天分析完后 | 聚合洞察 JSON |
| Prompt 3 行动建议 | 每个高风险 SKU | 7 天行动方案 |
| Prompt 4 周报 | 每周日 | Markdown 周报 |

## 为什么不直接合并成一个大 Prompt？

- **可调试**：单条判断的 prompt 可以单独调优，不影响其他流程
- **可缓存**：单条判断结果可以缓存 24 小时，CPSC 网站内容不变就不重复调用
- **可降级**：某个 prompt 失败时，其他 prompt 仍能跑
- **可观察**：每个 prompt 的 token 消耗可以分开统计，便于优化成本

## 提示词工程的几个关键点

1. **零编造约束**：每个 prompt 都强调"基于原文判断"，避免幻觉
2. **保守优先**：不确定的按 MEDIUM/LOW，宁可误报不可漏报
3. **结构化输出**：全部要求 JSON 或 Markdown，方便后续脚本解析
4. **不给废话**：明确要求"不给'建议尽快处理'这种空话"

## 测试用例（你要自己跑一遍）

准备 3 个测试公告（找 CPSC 最近一周的真实召回事件）：
- 测试 1：明显命中你的 SKU（应该返回 HIGH）
- 测试 2：同类目但不命中（应该返回 MEDIUM）
- 测试 3：完全无关（应该返回 LOW）

3 个测试都对，prompt 才算调好。