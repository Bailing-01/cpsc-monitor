"""
CPSC 公告抓取

支持 3 个数据源：
1. CPSC 官网 RSS（必抓）
2. CPSC.gov "SaferProducts" 数据库（必抓）
3. 亚马逊后台"账户状况"页面截图 OCR（可选）
"""

import logging
import feedparser
import requests
from datetime import date, timedelta
from pathlib import Path
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from cpsc_monitor.utils import retry

logger = logging.getLogger("cpsc-monitor.fetcher")


# CPSC 公开数据源
CPSC_RSS_URL = "https://www.cpsc.gov/cpscrecalls/rss"
SAFERPRODUCTS_API = "https://www.saferproducts.gov/RestWebServices/Recall"


@retry(max_attempts=3, delay_seconds=2, backoff=2)
def fetch_cpsc_rss(target_date: date) -> List[Dict[str, Any]]:
    """
    从 CPSC 官网 RSS 抓取最新公告

    Returns:
        公告列表，每条包含 title/url/published/summary
    """
    logger.info(f"  抓取 CPSC RSS: {CPSC_RSS_URL}")
    feed = feedparser.parse(CPSC_RSS_URL)

    if feed.bozo and not feed.entries:
        raise RuntimeError(f"CPSC RSS 解析失败：{feed.bozo_exception}")

    announcements = []
    cutoff = target_date - timedelta(days=1)  # 抓今天 + 昨天的

    for entry in feed.entries[:30]:  # 最多取 30 条
        # 解析发布时间
        published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if not published_parsed:
            continue

        from datetime import datetime
        published_dt = datetime(*published_parsed[:6]).date()
        if published_dt < cutoff:
            continue

        announcements.append({
            "title": entry.get("title", "").strip(),
            "url": entry.get("link", "").strip(),
            "published": published_dt.isoformat(),
            "summary": entry.get("summary", "").strip(),
            "source": "cpsc_rss",
            # 抓正文（可选）
            "content": _fetch_full_content(entry.get("link", "")),
        })

    logger.info(f"  RSS 抓到 {len(announcements)} 条公告")
    return announcements


def _fetch_full_content(url: str) -> str:
    """抓公告详情页正文（best-effort，失败不影响主流程）"""
    if not url:
        return ""

    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "cpsc-monitor/1.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # CPSC 页面正文通常在 article 或 main 标签
        content = soup.find("article") or soup.find("main") or soup.find("div", class_="field-items")
        return content.get_text(strip=True)[:3000] if content else ""
    except Exception as e:
        logger.debug(f"  抓公告正文失败：{url} - {e}")
        return ""


@retry(max_attempts=3, delay_seconds=2, backoff=2)
def fetch_saferproducts(target_date: date) -> List[Dict[str, Any]]:
    """
    从 SaferProducts.gov 数据库抓取召回事件

    Returns:
        公告列表
    """
    logger.info(f"  抓取 SaferProducts 数据库")
    try:
        params = {
            "RecallDateStart": (target_date - timedelta(days=2)).strftime("%Y-%m-%d"),
            "RecallDateEnd": target_date.strftime("%Y-%m-%d"),
            "format": "json",
        }
        response = requests.get(SAFERPRODUCTS_API, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        announcements = []
        for item in data if isinstance(data, list) else data.get("results", []):
            announcements.append({
                "title": item.get("RecallTitle", "").strip(),
                "url": f"https://www.saferproducts.gov/ViewRecall/{item.get('RecallID', '')}",
                "published": item.get("RecallDate", ""),
                "summary": item.get("HazardDescription", "")[:500],
                "source": "saferproducts",
                "content": item.get("Description", "")[:3000],
            })
        logger.info(f"  SaferProducts 抓到 {len(announcements)} 条")
        return announcements
    except Exception as e:
        logger.warning(f"  SaferProducts 抓取失败：{e}")
        return []


def fetch_announcements(config: dict, target_date: date) -> List[Dict[str, Any]]:
    """
    抓取所有数据源并合并去重

    Args:
        config: 配置字典
        target_date: 目标日期

    Returns:
        去重后的公告列表
    """
    all_announcements = []

    # Source 1: CPSC RSS（必抓）
    try:
        all_announcements.extend(fetch_cpsc_rss(target_date))
    except Exception as e:
        logger.error(f"  CPSC RSS 抓取最终失败：{e}")

    # Source 2: SaferProducts（必抓）
    try:
        all_announcements.extend(fetch_saferproducts(target_date))
    except Exception as e:
        logger.error(f"  SaferProducts 抓取最终失败：{e}")

    # Source 3: 亚马逊后台截图（可选）
    if config.get("amazon_account_screenshot", {}).get("enabled"):
        try:
            all_announcements.extend(fetch_amazon_screenshot(config, target_date))
        except Exception as e:
            logger.warning(f"  亚马逊后台截图解析失败：{e}")

    # 去重（按 URL）
    seen_urls = set()
    unique_announcements = []
    for ann in all_announcements:
        url = ann.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_announcements.append(ann)
        elif not url:
            unique_announcements.append(ann)

    # 保存原始公告到文件
    output_dir = Path(config.get("output", {}).get("dir", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_file = output_dir / f"{target_date.isoformat()}-raw-announcements.md"

    with raw_file.open("w", encoding="utf-8") as f:
        f.write(f"# CPSC 原始公告 - {target_date}\n\n")
        f.write(f"共 {len(unique_announcements)} 条公告\n\n")
        for i, ann in enumerate(unique_announcements, 1):
            f.write(f"## {i}. {ann['title']}\n\n")
            f.write(f"- **来源**: {ann['source']}\n")
            f.write(f"- **发布时间**: {ann['published']}\n")
            f.write(f"- **链接**: {ann['url']}\n")
            f.write(f"- **摘要**: {ann['summary']}\n\n")
            if ann.get('content'):
                f.write(f"### 正文\n\n{ann['content']}\n\n")
            f.write("---\n\n")

    logger.info(f"  原始公告已保存：{raw_file}")
    return unique_announcements


def fetch_amazon_screenshot(config: dict, target_date: date) -> List[Dict[str, Any]]:
    """
    解析亚马逊后台"账户状况"截图（OCR）

    这是一个可选功能，需要：
    1. 用户预先截图（用 Playwright 或手动）
    2. OCR 识别（用 pytesseract）
    """
    # 占位实现 - 实际需要 OCR 库
    logger.warning("  亚马逊后台 OCR 功能未实现，请用截图 + 手动填入")
    return []