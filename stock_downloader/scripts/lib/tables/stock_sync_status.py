#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票同步状态表 (stock_sync_status)
"""

from typing import Optional
import datetime
import pandas as pd
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class StockSyncStatusTable:
    """股票同步状态表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS stock_sync_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL UNIQUE,
                    last_sync_date TEXT,
                    sync_status TEXT,
                    update_time TEXT,
                    UNIQUE(ts_code)
                )
            """))
            conn.commit()
    
    def get(self, ts_code: str) -> Optional[dict]:
        """获取股票同步状态"""
        query = text("SELECT * FROM stock_sync_status WHERE ts_code = :ts_code")
        with self.db_conn.get_connection() as conn:
            result = conn.execute(query, {"ts_code": ts_code}).fetchone()
        if result:
            return {
                "ts_code": result[1],
                "last_sync_date": result[2],
                "sync_status": result[3],
                "update_time": result[4]
            }
        return None
    
    def update(self, ts_code: str, last_sync_date: str, sync_status: str = 'success'):
        """更新股票同步状态"""
        update_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                INSERT OR REPLACE INTO stock_sync_status (ts_code, last_sync_date, sync_status, update_time)
                VALUES (:ts_code, :last_sync_date, :sync_status, :update_time)
            """), {
                "ts_code": ts_code,
                "last_sync_date": last_sync_date,
                "sync_status": sync_status,
                "update_time": update_time
            })
            conn.commit()
    
    def get_all(self) -> pd.DataFrame:
        """获取所有股票的同步状态"""
        query = "SELECT * FROM stock_sync_status ORDER BY ts_code"
        return pd.read_sql(text(query), self.db_conn.engine)