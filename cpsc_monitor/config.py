"""
配置加载和验证
"""

import yaml
from pathlib import Path
from typing import Any, Dict


CONFIG_PATH = Path("config.yaml")


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    """
    加载 config.yaml 并做基本校验

    Raises:
        FileNotFoundError: config.yaml 不存在
        AssertionError: 必填字段缺失或格式不对
    """
    if not path.exists():
        raise FileNotFoundError(
            f"配置文件不存在：{path}\n"
            f"请先复制 config.example.yaml 为 {path.name} 并填写 SKU 列表和告警邮箱"
        )

    config = yaml.safe_load(path.read_text(encoding="utf-8"))

    # 校验必填字段
    assert "my_skus" in config, "配置缺少 my_skus 字段"
    assert isinstance(config["my_skus"], list), "my_skus 必须是列表"
    assert len(config["my_skus"]) >= 10, f"至少填 10 个 SKU，当前 {len(config['my_skus'])} 个"

    assert "alert_emails" in config, "配置缺少 alert_emails 字段"
    assert isinstance(config["alert_emails"], list), "alert_emails 必须是列表"
    assert len(config["alert_emails"]) >= 1, "至少填 1 个告警邮箱"
    for email in config["alert_emails"]:
        assert "@" in email, f"告警邮箱格式不对：{email}"

    # 校验每个 SKU 的必填字段
    for i, sku in enumerate(config["my_skus"]):
        assert "name" in sku, f"第 {i+1} 个 SKU 缺少 name 字段"
        assert "asin" in sku, f"第 {i+1} 个 SKU 缺少 asin 字段"
        assert "keywords" in sku, f"第 {i+1} 个 SKU 缺少 keywords 字段"
        assert isinstance(sku["keywords"], list), f"第 {i+1} 个 SKU 的 keywords 必须是列表"

    # 设置默认值
    if "sms" not in config:
        config["sms"] = {"enabled": False}
    if "ai" not in config:
        config["ai"] = {"provider": "anthropic", "model": "claude-sonnet-4-20250514", "temperature": 0.1, "max_tokens": 4000}
    if "fetch" not in config:
        config["fetch"] = {"retry_times": 3, "timeout_seconds": 30}
    if "output" not in config:
        config["output"] = {"dir": "./output"}
    if "history" not in config:
        config["history"] = {"retention_days": 90, "log_path": "./history.yaml"}

    return config