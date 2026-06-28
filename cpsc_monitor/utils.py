"""
工具函数：日志、重试、目录管理
"""

import logging
import sys
import time
from pathlib import Path
from functools import wraps
from datetime import datetime


def setup_logging(log_dir: str = "logs", log_file: str = "cpsc-monitor.log"):
    """配置日志：控制台 + 文件"""
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(log_format)

    # 控制台
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # 文件
    log_path = Path(log_dir) / log_file
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def ensure_dirs(dirs):
    """确保目录存在"""
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


def retry(max_attempts: int = 3, delay_seconds: int = 2, backoff: int = 2):
    """
    重试装饰器（指数退避）

    Args:
        max_attempts: 最大尝试次数
        delay_seconds: 初始延迟秒数
        backoff: 退避倍数（2 = 2, 4, 8 秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            last_exception = RuntimeError("retry 装饰器未捕获到异常")
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts:
                        wait_time = delay_seconds * (backoff ** (attempt - 1))
                        logger.warning(
                            f"{func.__name__} 第 {attempt}/{max_attempts} 次失败：{e}"
                            f"，{wait_time} 秒后重试"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"{func.__name__} 已重试 {max_attempts} 次仍失败：{e}")

            raise last_exception
        return wrapper
    return decorator


def log_run(log_dir: str = "logs"):
    """记录每次运行开始"""
    log_file = Path(log_dir) / "runs.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] run.py started\n")