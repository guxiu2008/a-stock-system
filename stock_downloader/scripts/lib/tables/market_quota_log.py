#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行情同步日志表 (market_quota_log)
"""

import datetime
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class MarketQuotaLogTable:
    """行情同步日志表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS market_quota_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_type TEXT NOT NULL,
                    ts_code TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    update_time TEXT NOT NULL,
                    record_count INTEGER,
                    status TEXT
                )
            """))
            conn.commit()
    
    def log(self, sync_type: str, ts_code: str, start_date: str, 
            end_date: str, record_count: int, status: str):
        """记录同步日志"""
        update_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                INSERT INTO market_quota_log (sync_type, ts_code, start_date, end_date, update_time, record_count, status)
                VALUES (:sync_type, :ts_code, :start_date, :end_date, :update_time, :record_count, :status)
            """), {
                "sync_type": sync_type,
                "ts_code": ts_code,
                "start_date": start_date,
                "end_date": end_date,
                "update_time": update_time,
                "record_count": record_count,
                "status": status
            })
            conn.commit()