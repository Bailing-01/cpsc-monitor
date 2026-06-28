"""
CPSC 公告抓取（Playwright stealth 版本）

主要数据源：CPSC 官网（用 Playwright 真实浏览器绕过 Akamai 反爬）
降级数据源：CPSC RSS（用 feedparser，作为备份）

注意：
- 首次抓取通常成功
- 连续抓取可能被 Akamai 风控（每天只跑 1 次可降低风险）
- stealth 插件能绕过 80% 检测，但不是 100%
"""

import logging
import random
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from cpsc_monitor.utils import retry

logger = logging.getLogger("cpsc-monitor.fetcher")


# CPSC 数据源
CPSC_RECALLS_URL = "https://www.cpsc.gov/Recalls"
CPSC_RSS_URL = "https://www.cpsc.gov/cpscrecalls/rss"


# ============================================================
# 主数据源：用 Playwright 抓 CPSC Recalls 页面
# ============================================================

def _fetch_with_playwright(url: str, wait_selector: Optional[str] = None) -> str:
    """
    用 Playwright 真实浏览器抓 URL

    Args:
        url: 目标 URL
        wait_selector: 等待这个 selector 出现再返回（可选）

    Returns:
        页面 HTML
    """
    from playwright.sync_api import sync_playwright
    from playwright_stealth import Stealth

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="America/New_York",
        )
        page = context.new_page()

        # 应用 stealth 反检测（新 API）
        stealth = Stealth()
        stealth.apply_stealth_sync(page)

        # 慢速抓取：先访问首页建立 cookie，再访问目标
        # 这一步绕过 Akamai 第一次访问的风控
        logger.debug(f"  第一次访问 cpsc.gov 首页...")
        page.goto("https://www.cpsc.gov/", wait_until="domcontentloaded", timeout=30000)
        time.sleep(random.uniform(1.5, 3.0))  # 模拟人类浏览

        logger.debug(f"  第二次访问目标: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # 如果指定了 selector，等待它出现
        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=15000)
            except Exception as e:
                logger.warning(f"  等待 selector '{wait_selector}' 超时：{e}")

        # 慢一点，让 JS 跑完
        time.sleep(random.uniform(2.0, 4.0))

        content = page.content()
        browser.close()
        return content


def _parse_cpsc_recalls_html(html: str) -> List[Dict[str, Any]]:
    """
    解析 CPSC Recalls 页面 HTML，提取公告列表

    CPSC Drupal 页面结构（2026 年）：
    - 每个 recall 是一个 view-row 或 article 标签
    - 标题在 h2/h3 内，链接指向 /Recalls/[year]/[slug]
    """
    from bs4 import BeautifulSoup
    import re

    soup = BeautifulSoup(html, "html.parser")
    announcements = []

    # 找所有 /Recalls/[year]/... 格式的链接（真实召回公告）
    # 排除导航链接如 /Recalls/API、/Recalls/violations 等
    all_recall_links = soup.select('a[href*="/Recalls/"]')
    real_recall_links = [
        a for a in all_recall_links
        if re.search(r'/Recalls/\d{4}/', a.get('href', ''))
    ]

    seen_urls = set()
    for link in real_recall_links:
        href = link.get("href", "")
        if not href or "/Recalls/" not in href:
            continue

        # 拼完整 URL
        if href.startswith("/"):
            full_url = f"https://www.cpsc.gov{href}"
        elif href.startswith("http"):
            full_url = href
        else:
            continue

        # 去重
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # 提取标题
        title = link.get_text(strip=True)
        # 过滤过短或纯导航的标题
        if not title or len(title) < 15:
            continue
        if title.lower() in ("previously recalled", "view all", "see more", "read more"):
            continue

        announcements.append({
            "title": title,
            "url": full_url,
            "published": "",  # HTML 里通常没日期，要进详情页
            "summary": "",
            "source": "cpsc_recalls",
            "content": "",  # 列表页没正文
        })

    logger.debug(f"  HTML 解析出 {len(announcements)} 个公告")
    return announcements


def _fetch_recall_detail(url: str) -> Dict[str, str]:
    """
    抓单个公告详情页，提取发布日期和摘要

    Returns:
        {"published": "YYYY-MM-DD", "summary": "..."}
    """
    try:
        html = _fetch_with_playwright(url)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser") if html else None
        if not soup:
            return {}

        # 找日期（CPSC 页面通常在 .field--name-field-recall-date 或 .date-display-single）
        date_elem = (
            soup.select_one(".date-display-single")
            or soup.select_one('[property="dc:date"]')
            or soup.select_one("time")
        )
        published = ""
        if date_elem:
            published = date_elem.get("content") or date_elem.get_text(strip=True)

        # 找摘要（recall 描述）
        summary_elem = (
            soup.select_one(".field--name-body")
            or soup.select_one("article p")
        )
        summary = ""
        if summary_elem:
            summary = summary_elem.get_text(strip=True)[:500]

        return {"published": published, "summary": summary, "content": summary[:3000]}
    except Exception as e:
        logger.debug(f"  抓详情失败 {url}: {e}")
        return {}


# ============================================================
# 备份数据源：用 feedparser 抓 RSS（可能 403，但试一下）
# ============================================================

def _fetch_cpsc_rss() -> List[Dict[str, Any]]:
    """尝试用 feedparser 抓 RSS（可能 403）"""
    import feedparser
    try:
        feed = feedparser.parse(CPSC_RSS_URL)
        if feed.bozo and not feed.entries:
            logger.warning(f"  RSS 解析失败（可能被 Akamai 挡）: {feed.bozo_exception}")
            return []
        if not feed.entries:
            return []

        announcements = []
        for entry in feed.entries[:30]:
            announcements.append({
                "title": entry.get("title", "").strip(),
                "url": entry.get("link", "").strip(),
                "published": entry.get("published", ""),
                "summary": entry.get("summary", "").strip()[:500],
                "source": "cpsc_rss",
                "content": "",
            })
        logger.info(f"  RSS 抓到 {len(announcements)} 条")
        return announcements
    except Exception as e:
        logger.warning(f"  RSS 抓取失败：{e}")
        return []


# ============================================================
# 主函数
# ============================================================

@retry(max_attempts=3, delay_seconds=5, backoff=2)
def fetch_announcements(config: dict, target_date: date) -> List[Dict[str, Any]]:
    """
    抓取 CPSC 公告（Playwright + stealth 主路径，RSS 备份）

    Args:
        config: 配置字典
        target_date: 目标日期

    Returns:
        去重后的公告列表
    """
    logger.info(f"  抓取 CPSC Recalls 页面: {CPSC_RECALLS_URL}")
    all_announcements = []

    try:
        # 主路径：Playwright 抓 CPSC Recalls 列表页
        html = _fetch_with_playwright(CPSC_RECALLS_URL, wait_selector='a[href*="/Recalls/"]')
        list_announcements = _parse_cpsc_recalls_html(html)
        logger.info(f"  列表页解析出 {len(list_announcements)} 个公告")

        # 给前 3 条公告抓详情（避免超时，详情抓太多会触发 Akamai）
        # V2 优化：异步批量抓详情
        for i, ann in enumerate(list_announcements[:3], 1):
            logger.debug(f"  [{i}/3] 抓详情: {ann['url']}")
            detail = _fetch_recall_detail(ann["url"])
            ann.update(detail)
            # 慢速：每次间隔 2-3 秒
            if i < len(list_announcements[:3]):
                time.sleep(random.uniform(2.0, 3.0))

        all_announcements.extend(list_announcements)

    except Exception as e:
        logger.error(f"  Playwright 主路径失败：{e}")

    # 备份路径：RSS（如果主路径失败或抓到 0 条）
    if not all_announcements:
        logger.info("  主路径无结果，尝试 RSS 备份")
        rss_announcements = _fetch_cpsc_rss()
        all_announcements.extend(rss_announcements)

    # 去重
    seen_urls = set()
    unique = []
    for ann in all_announcements:
        url = ann.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(ann)
        elif not url:
            unique.append(ann)

    # 保存原始公告到文件
    output_dir = Path(config.get("output", {}).get("dir", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_file = output_dir / f"{target_date.isoformat()}-raw-announcements.md"

    with raw_file.open("w", encoding="utf-8") as f:
        f.write(f"# CPSC 原始公告 - {target_date}\n\n")
        f.write(f"共 {len(unique)} 条公告\n\n")
        for i, ann in enumerate(unique, 1):
            f.write(f"## {i}. {ann['title']}\n\n")
            f.write(f"- **来源**: {ann['source']}\n")
            f.write(f"- **发布时间**: {ann['published'] or '未提取'}\n")
            f.write(f"- **链接**: {ann['url']}\n")
            if ann.get("summary"):
                f.write(f"- **摘要**: {ann['summary']}\n")
            f.write("\n---\n\n")

    logger.info(f"  原始公告已保存：{raw_file}")
    return unique


def fetch_amazon_screenshot(config: dict, target_date: date) -> List[Dict[str, Any]]:
    """亚马逊后台截图 OCR（V2 占位）"""
    logger.warning("  亚马逊后台 OCR 功能未实现")
    return []