#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产注册表日志表 (asset_registry_log)
"""

from typing import Optional
import datetime
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class AssetRegistryLogTable:
    """资产注册表更新日志表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS asset_registry_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_type TEXT NOT NULL,
                    update_time TEXT NOT NULL,
                    record_count INTEGER,
                    status TEXT
                )
            """))
            conn.commit()
    
    def log(self, data_type: str, record_count: int, status: str):
        """记录更新日志"""
        update_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                INSERT INTO asset_registry_log (data_type, update_time, record_count, status)
                VALUES (:data_type, :update_time, :record_count, :status)
            """), {
                "data_type": data_type,
                "update_time": update_time,
                "record_count": record_count,
                "status": status
            })
            conn.commit()
    
    def get_last_update_time(self, data_type: str) -> Optional[str]:
        """获取指定数据类型的最后更新时间"""
        with self.db_conn.get_connection() as conn:
            result = conn.execute(
                text("SELECT update_time FROM asset_registry_log WHERE data_type = :data_type ORDER BY update_time DESC LIMIT 1"),
                {"data_type": data_type}
            ).fetchone()
        return result[0] if result else None