"""
历史记录管理
"""

import logging
import yaml
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("cpsc-monitor.history")


def update_history(target_date: date, stats: Dict[str, Any]):
    """
    追加一条历史记录

    Args:
        target_date: 运行日期
        stats: 统计信息（announcement_count / high / medium / low / themes）
    """
    history_path = Path("history.yaml")
    history = _load_history(history_path)

    record = {
        "date": target_date.isoformat(),
        "timestamp": datetime.now().isoformat(),
        **stats,
    }

    # 避免重复（同一天多次跑只保留最新）
    history["runs"] = [r for r in history.get("runs", []) if r.get("date") != target_date.isoformat()]
    history["runs"].append(record)

    # 按日期排序
    history["runs"].sort(key=lambda r: r.get("date", ""))

    # 保留最近 N 天的记录
    from cpsc_monitor.config import load_config  # 延迟导入避免循环
    try:
        config = load_config()
        retention_days = config.get("history", {}).get("retention_days", 90)
    except Exception:
        retention_days = 90

    cutoff = date.today().toordinal() - retention_days
    history["runs"] = [
        r for r in history["runs"]
        if date.fromisoformat(r["date"]).toordinal() >= cutoff
    ]

    history_path.write_text(
        yaml.safe_dump(history, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    logger.info(f"  历史记录已更新：{history_path}（共 {len(history['runs'])} 条）")


def _load_history(path: Path) -> Dict[str, Any]:
    """加载历史记录（不存在则返回空 dict）"""
    if not path.exists():
        return {"runs": []}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"runs": []}


def get_recent_runs(days: int = 7) -> list:
    """获取最近 N 天的运行记录"""
    history = _load_history(Path("history.yaml"))
    cutoff = date.today().toordinal() - days
    return [
        r for r in history.get("runs", [])
        if date.fromisoformat(r["date"]).toordinal() >= cutoff
    ]