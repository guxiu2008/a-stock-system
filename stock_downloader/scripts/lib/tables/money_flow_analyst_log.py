#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金流向分析日志表 (money_flow_analyst_log)
"""

from typing import Optional
import datetime
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class MoneyFlowAnalystLogTable:
    """资金流向分析日志表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS money_flow_analyst_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    data_type TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    record_count INTEGER,
                    status TEXT,
                    error_msg TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """))
            conn.commit()
    
    def log_start(self, action_type: str, data_type: str = None, start_date: str = None, end_date: str = None) -> int:
        """记录开始日志"""
        created_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.db_conn.get_connection() as conn:
            result = conn.execute(text("""
                INSERT INTO money_flow_analyst_log (action_type, data_type, start_date, end_date, status, created_at, updated_at)
                VALUES (:action_type, :data_type, :start_date, :end_date, 'running', :created_at, :created_at)
            """), {
                "action_type": action_type,
                "data_type": data_type,
                "start_date": start_date,
                "end_date": end_date,
                "created_at": created_at
            })
            conn.commit()
            return result.lastrowid
    
    def log_success(self, log_id: int, record_count: int = 0):
        """记录成功日志"""
        updated_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                UPDATE money_flow_analyst_log 
                SET status = 'success', record_count = :record_count, updated_at = :updated_at
                WHERE id = :log_id
            """), {
                "log_id": log_id,
                "record_count": record_count,
                "updated_at": updated_at
            })
            conn.commit()
    
    def log_error(self, log_id: int, error_msg: str):
        """记录错误日志"""
        updated_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                UPDATE money_flow_analyst_log 
                SET status = 'error', error_msg = :error_msg, updated_at = :updated_at
                WHERE id = :log_id
            """), {
                "log_id": log_id,
                "error_msg": error_msg,
                "updated_at": updated_at
            })
            conn.commit()
    
    def get_last_update_time(self, action_type: str) -> Optional[str]:
        """获取指定操作类型的最后更新时间"""
        query = text("""
            SELECT MAX(updated_at) FROM money_flow_analyst_log 
            WHERE action_type = :action_type AND status = 'success'
        """)
        with self.db_conn.get_connection() as conn:
            result = conn.execute(query, {"action_type": action_type}).fetchone()
        return result[0] if result and result[0] else None