#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分红历史表 (fact_dividend_history)
存储股票分红送股数据
"""

import pandas as pd
from sqlalchemy import text
from typing import Optional
from scripts.lib.base import DatabaseConnection


class FactDividendHistoryTable:
    """分红历史表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS fact_dividend_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    ann_date TEXT,
                    end_date TEXT NOT NULL,
                    cash_div_tax REAL,
                    record_date TEXT,
                    ex_date TEXT,
                    div_proc TEXT,
                    payout_ratio REAL,
                    update_time TEXT NOT NULL,
                    UNIQUE(ts_code, end_date, ann_date)
                )
            """))
            conn.commit()
    
    def save(self, df: pd.DataFrame) -> int:
        """
        保存分红数据
        
        Args:
            df: 分红数据DataFrame，需要包含 ts_code, end_date 等字段
        
        Returns:
            保存的记录数
        """
        if df.empty:
            return 0
        
        # 使用INSERT OR REPLACE处理重复数据
        with self.db_conn.get_connection() as conn:
            count = 0
            for _, row in df.iterrows():
                conn.execute(text("""
                    INSERT OR REPLACE INTO fact_dividend_history 
                    (ts_code, ann_date, end_date, cash_div_tax, record_date, ex_date, div_proc, payout_ratio, update_time)
                    VALUES (:ts_code, :ann_date, :end_date, :cash_div_tax, :record_date, :ex_date, :div_proc, :payout_ratio, :update_time)
                """), {
                    "ts_code": row.get("ts_code"),
                    "ann_date": row.get("ann_date"),
                    "end_date": row.get("end_date"),
                    "cash_div_tax": row.get("cash_div_tax"),
                    "record_date": row.get("record_date"),
                    "ex_date": row.get("ex_date"),
                    "div_proc": row.get("div_proc"),
                    "payout_ratio": row.get("payout_ratio"),
                    "update_time": row.get("update_time")
                })
                count += 1
            conn.commit()
        return count
    
    def get_by_ts_code(self, ts_code: str) -> pd.DataFrame:
        """
        获取指定股票的分红数据
        
        Args:
            ts_code: 股票代码
        
        Returns:
            分红数据DataFrame
        """
        with self.db_conn.get_connection() as conn:
            df = pd.read_sql(
                text("SELECT * FROM fact_dividend_history WHERE ts_code = :ts_code ORDER BY end_date DESC"),
                conn,
                params={"ts_code": ts_code}
            )
        return df
    
    def get_by_end_date(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取指定时间范围内的分红数据
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            分红数据DataFrame
        """
        with self.db_conn.get_connection() as conn:
            df = pd.read_sql(
                text("SELECT * FROM fact_dividend_history WHERE end_date BETWEEN :start_date AND :end_date ORDER BY end_date DESC"),
                conn,
                params={"start_date": start_date, "end_date": end_date}
            )
        return df
    
    def get_all(self) -> pd.DataFrame:
        """
        获取所有分红数据
        
        Returns:
            分红数据DataFrame
        """
        with self.db_conn.get_connection() as conn:
            df = pd.read_sql(text("SELECT * FROM fact_dividend_history ORDER BY end_date DESC"), conn)
        return df
    
    def get_latest_year(self, ts_code: str) -> Optional[str]:
        """
        获取指定股票最新的分红年度
        
        Args:
            ts_code: 股票代码
        
        Returns:
            最新分红年度，格式YYYYMMDD
        """
        with self.db_conn.get_connection() as conn:
            result = conn.execute(
                text("SELECT end_date FROM fact_dividend_history WHERE ts_code = :ts_code ORDER BY end_date DESC LIMIT 1"),
                {"ts_code": ts_code}
            ).fetchone()
        return result[0] if result else None
    
    def clear(self):
        """清空表"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("DELETE FROM fact_dividend_history"))
            conn.commit()