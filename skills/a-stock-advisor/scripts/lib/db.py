#!/usr/bin/env python3
"""
数据库连接管理
"""
import os
import sqlite3
import pandas as pd

DEFAULT_DB = os.getenv("STOCK_DB_PATH", "/workspace/stock_downloader/stock_data.db")


def get_conn(db_path: str = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"股票数据库不存在: {path}\n"
            f"请确保已下载数据，或设置 STOCK_DB_PATH 环境变量指向正确的路径。\n"
            f"数据下载方式: cd stock_downloader && ./run.sh"
        )
    return sqlite3.connect(path)


def check_db_ready(conn: sqlite3.Connection = None) -> tuple:
    """检查数据库是否就绪，返回 (ok: bool, message: str)"""
    close = False
    if conn is None:
        conn = get_conn()
        close = True
    try:
        # 检查必要表是否存在且有数据
        cur = conn.execute("SELECT COUNT(*) FROM dim_stock_info")
        stocks = cur.fetchone()[0]
        cur = conn.execute("SELECT MAX(trade_date) FROM fact_daily_quotes")
        latest = cur.fetchone()[0]
        cur = conn.execute("SELECT COUNT(*) FROM market_indicators WHERE trade_date = (SELECT MAX(trade_date) FROM market_indicators)")
        today_count = cur.fetchone()[0]

        if stocks == 0:
            return (False, "数据库为空，请先运行 asset_registry 初始化股票数据")
        if latest is None:
            return (False, "无行情数据，请先运行 market_quota_syncer")

        return (True, f"就绪: {stocks} 只股票, 最新交易日 {latest}, 今日指标 {today_count} 只")
    finally:
        if close:
            conn.close()