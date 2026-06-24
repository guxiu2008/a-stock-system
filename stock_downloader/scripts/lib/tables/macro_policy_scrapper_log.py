#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观政策抓取日志表 (macro_policy_scrapper_log)
"""

from typing import Optional
import datetime
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class MacroPolicyScrapperLogTable:
    """宏观政策抓取日志表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS macro_policy_scrapper_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    update_time TEXT NOT NULL,
                    record_count INTEGER,
                    status TEXT,
                    message TEXT
                )
            """))
            conn.commit()
    
    def log(self, data_type: str, source: str, record_count: int, status: str, message: Optional[str] = None):
        """
        记录更新日志
        
        Args:
            data_type: 数据类型 (news, eco_cal, xwlb, meeting, etc.)
            source: 数据来源
            record_count: 记录数
            status: 状态 (success, failed, partial)
            message: 附加信息
        """
        update_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                INSERT INTO macro_policy_scrapper_log (data_type, source, update_time, record_count, status, message)
                VALUES (:data_type, :source, :update_time, :record_count, :status, :message)
            """), {
                "data_type": data_type,
                "source": source,
                "update_time": update_time,
                "record_count": record_count,
                "status": status,
                "message": message
            })
            conn.commit()
    
    def get_last_update_time(self, data_type: str, source: Optional[str] = None) -> Optional[str]:
        """
        获取指定数据类型的最后更新时间
        
        Args:
            data_type: 数据类型
            source: 数据来源（可选）
        
        Returns:
            最后更新时间
        """
        query = """
            SELECT update_time FROM macro_policy_scrapper_log 
            WHERE data_type = :data_type 
        """
        params = {"data_type": data_type}
        
        if source:
            query += " AND source = :source"
            params["source"] = source
        
        query += " ORDER BY update_time DESC LIMIT 1"
        
        with self.db_conn.get_connection() as conn:
            result = conn.execute(text(query), params).fetchone()
        
        return result[0] if result else None
    
    def clear(self):
        """清空表"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("DELETE FROM macro_policy_scrapper_log"))
            conn.commit()