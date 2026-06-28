"""
AI 风险分析

调用 Anthropic Claude / OpenAI / Google Gemini 做风险判断。
支持 4 个 prompt：
1. Prompt 1: 单条公告判断
2. Prompt 2: 多条公告聚合
3. Prompt 3: 行动建议生成（v2 待实现）
4. Prompt 4: 周报生成（v2 待实现）
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("cpsc-monitor.ai_analyzer")


def _load_prompt_template(prompt_name: str) -> str:
    """加载 prompt 模板（从 prompt-template.md 抽出来）"""
    # 这里用内置的简化版 prompt
    # 完整版在仓库根目录的 prompt-template.md，供用户参考
    prompts = {
        "single": SINGLE_ANNOUNCEMENT_PROMPT,
        "summary": SUMMARY_PROMPT,
    }
    return prompts.get(prompt_name, "")


SINGLE_ANNOUNCEMENT_PROMPT = """你是亚马逊合规顾问，专长是 CPSC（美国消费品安全委员会）合规风险识别。

【任务】
判断以下 CPSC 公告是否与我的产品库相关，并评估风险等级。

【CPSC 公告】
标题：{title}
发布时间：{published}
摘要：{summary}
正文：{content}

【我的产品库】
{sku_list}

【输出要求】
严格按 JSON 输出，不要任何额外文字：

```json
{{
  "is_relevant": true/false,
  "matched_skus": [
    {{
      "sku_name": "...",
      "asin": "...",
      "match_reason": "...",
      "specific_risk": "..."
    }}
  ],
  "risk_level": "high" / "medium" / "low",
  "risk_rationale": "...",
  "action_required": ["动作1", "动作2", "动作3"],
  "deadline_days": 14,
  "compliance_docs_needed": ["UL 报告", "..."],
  "estimated_cost_usd": 0,
  "source_url": "{url}"
}}
```

【判断标准】
- HIGH：直接命中 SKU 关键词 + 涉及人身安全（火灾/窒息/中毒/电击）
- MEDIUM：涉及同类目但不直接命中，或非安全类合规
- LOW：完全不相关

【重要】零编造，所有判断必须基于公告原文。"""


SUMMARY_PROMPT = """你是亚马逊合规顾问。基于以下今日 CPSC 公告和风险判断，输出聚合分析。

【今日公告 + 风险判断】
{announcements_with_risk}

【输出 JSON】
```json
{{
  "summary_by_risk": {{
    "high_count": 0,
    "medium_count": 0,
    "low_count": 0
  }},
  "todays_themes": ["主题1", "主题2"],
  "recurring_categories_7d": ["品类A"],
  "next_week_prediction": "下周 CPSC 可能重点关注...",
  "top_3_attention": [
    {{"rank": 1, "title": "...", "sku_impact": "..."}}
  ]
}}
```"""


def _call_anthropic(prompt: str, config: dict) -> str:
    """调用 Anthropic Claude API"""
    try:
        from anthropic import Anthropic
    except ImportError:
        raise RuntimeError("anthropic 库未安装，请 pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("环境变量 ANTHROPIC_API_KEY 未设置")

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=config["ai"].get("model", "claude-sonnet-4-20250514"),
        max_tokens=config["ai"].get("max_tokens", 4000),
        temperature=config["ai"].get("temperature", 0.1),
        messages=[{"role": "user", "content": prompt}],
    )
    # 提取 text block（可能有 thinking block 混在里面）
    text_parts = []
    for block in response.content:
        if hasattr(block, "text") and isinstance(getattr(block, "text", None), str):
            text_parts.append(block.text)
    return "\n".join(text_parts) if text_parts else str(response.content[0])


def _call_openai(prompt: str, config: dict) -> str:
    """调用 OpenAI API"""
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai 库未安装")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("环境变量 OPENAI_API_KEY 未设置")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=config["ai"].get("model", "gpt-4o"),
        max_tokens=config["ai"].get("max_tokens", 4000),
        temperature=config["ai"].get("temperature", 0.1),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def _call_ai(prompt: str, config: dict) -> str:
    """根据配置选择 AI provider"""
    provider = config["ai"].get("provider", "anthropic")
    if provider == "anthropic":
        return _call_anthropic(prompt, config)
    elif provider == "openai":
        return _call_openai(prompt, config)
    elif provider == "google":
        return _call_google(prompt, config)
    else:
        raise RuntimeError(f"不支持的 AI provider: {provider}")


def _call_google(prompt: str, config: dict) -> str:
    """调用 Google Gemini API"""
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError("google-generativeai 库未安装")

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("环境变量 GOOGLE_API_KEY 未设置")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(config["ai"].get("model", "gemini-2.0-flash-exp"))
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": config["ai"].get("temperature", 0.1),
            "max_output_tokens": config["ai"].get("max_tokens", 4000),
        }
    )
    return response.text


def _extract_json(ai_response: str) -> Dict[str, Any]:
    """从 AI 回复中提取 JSON（兼容 markdown 代码块格式）"""
    # 尝试找 ```json ... ``` 块
    if "```json" in ai_response:
        start = ai_response.find("```json") + 7
        end = ai_response.find("```", start)
        json_str = ai_response[start:end].strip()
    elif "```" in ai_response:
        start = ai_response.find("```") + 3
        end = ai_response.find("```", start)
        json_str = ai_response[start:end].strip()
    else:
        json_str = ai_response.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"AI 返回 JSON 解析失败：{e}")
        logger.debug(f"原始回复：{ai_response[:500]}")
        # 返回降级结果
        return {
            "is_relevant": False,
            "matched_skus": [],
            "risk_level": "low",
            "risk_rationale": f"AI 返回格式异常，已降级：{e}",
            "action_required": ["检查 AI 返回格式"],
            "deadline_days": 0,
            "compliance_docs_needed": [],
            "estimated_cost_usd": 0,
            "source_url": "",
            "_parse_error": True,
        }


def analyze_risks(announcements: List[Dict[str, Any]], config: dict) -> List[Dict[str, Any]]:
    """
    对每条公告调用 AI 做风险判断

    Args:
        announcements: 公告列表（来自 fetcher）
        config: 配置字典

    Returns:
        风险分析结果列表（与 announcements 一一对应）
    """
    sku_list_yaml = _format_sku_list(config["my_skus"])
    prompt_template = _load_prompt_template("single")
    results = []

    for i, ann in enumerate(announcements, 1):
        logger.info(f"  [{i}/{len(announcements)}] 分析公告：{ann.get('title', '')[:50]}")

        prompt = prompt_template.format(
            title=ann.get("title", ""),
            published=ann.get("published", ""),
            summary=ann.get("summary", ""),
            content=ann.get("content", "")[:2000],  # 截断避免超 token
            sku_list=sku_list_yaml,
            url=ann.get("url", ""),
        )

        try:
            ai_response = _call_ai(prompt, config)
            risk_data = _extract_json(ai_response)
            risk_data["_announcement"] = ann  # 保留原始公告引用
            results.append(risk_data)
        except Exception as e:
            logger.error(f"  AI 调用失败：{e}")
            # 降级：标为低风险
            results.append({
                "is_relevant": False,
                "matched_skus": [],
                "risk_level": "low",
                "risk_rationale": f"AI 调用失败：{e}",
                "action_required": [],
                "deadline_days": 0,
                "compliance_docs_needed": [],
                "estimated_cost_usd": 0,
                "source_url": ann.get("url", ""),
                "_announcement": ann,
                "_error": True,
            })

    # 保存 JSON 结果
    output_dir = Path(config.get("output", {}).get("dir", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    from datetime import date as _date
    today = _date.today()
    json_file = output_dir / f"{today.isoformat()}-risk-analysis.json"
    with json_file.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"  风险分析 JSON 已保存：{json_file}")

    return results


def summarize_announcements(announcements: List[Dict[str, Any]], risk_analysis: List[Dict[str, Any]], config: dict) -> Dict[str, Any]:
    """
    聚合分析：把所有公告 + 风险判断喂给 AI，输出日报级洞察

    Returns:
        聚合分析结果
    """
    # 准备输入：公告 + 风险判断
    combined = []
    for ann, risk in zip(announcements, risk_analysis):
        combined.append({
            "title": ann.get("title", ""),
            "summary": ann.get("summary", "")[:300],
            "risk_level": risk.get("risk_level", "low"),
            "matched_skus": [s.get("sku_name") for s in risk.get("matched_skus", [])],
        })

    prompt = SUMMARY_PROMPT.format(
        announcements_with_risk=json.dumps(combined, ensure_ascii=False, indent=2)
    )

    try:
        ai_response = _call_ai(prompt, config)
        summary = _extract_json(ai_response)
    except Exception as e:
        logger.error(f"聚合分析 AI 调用失败：{e}，使用本地聚合")
        # 降级：本地统计
        summary = {
            "summary_by_risk": {
                "high_count": sum(1 for r in risk_analysis if r.get("risk_level") == "high"),
                "medium_count": sum(1 for r in risk_analysis if r.get("risk_level") == "medium"),
                "low_count": sum(1 for r in risk_analysis if r.get("risk_level") == "low"),
            },
            "todays_themes": [],
            "recurring_categories_7d": [],
            "next_week_prediction": "AI 聚合失败，建议人工查看",
            "top_3_attention": [],
            "_error": str(e),
        }

    # 保存
    output_dir = Path(config.get("output", {}).get("dir", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    from datetime import date as _date
    today = _date.today()
    summary_file = output_dir / f"{today.isoformat()}-summary.json"
    with summary_file.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    logger.info(f"  聚合分析已保存：{summary_file}")

    return summary


def _format_sku_list(skus: List[Dict[str, Any]]) -> str:
    """把 SKU 列表格式化成 YAML 风格文本"""
    lines = []
    for sku in skus:
        lines.append(f"- name: {sku.get('name', '')}")
        lines.append(f"  asin: {sku.get('asin', '')}")
        if sku.get("hs_code"):
            lines.append(f"  hs_code: {sku['hs_code']}")
        lines.append(f"  keywords: {', '.join(sku.get('keywords', []))}")
        if sku.get("category"):
            lines.append(f"  category: {sku['category']}")
        lines.append("")
    return "\n".join(lines)