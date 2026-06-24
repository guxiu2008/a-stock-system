#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
指数日线行情表 (fact_index_daily)
"""

from typing import Optional
import datetime
import pandas as pd
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class FactIndexDailyTable:
    """指数日线行情表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS fact_index_daily (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    pre_close REAL,
                    change REAL,
                    pct_chg REAL,
                    vol REAL,
                    amount REAL,
                    update_time TEXT,
                    UNIQUE(ts_code, trade_date)
                )
            """))
            conn.commit()
    
    def save(self, df: pd.DataFrame) -> int:
        """保存指数日线行情数据"""
        if df.empty:
            return 0
        
        df['update_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        ts_codes = df['ts_code'].unique()
        for ts_code in ts_codes:
            dates = df[df['ts_code'] == ts_code]['trade_date'].tolist()
            for trade_date in dates:
                with self.db_conn.get_connection() as conn:
                    conn.execute(
                        text("DELETE FROM fact_index_daily WHERE ts_code = :ts_code AND trade_date = :trade_date"),
                        {"ts_code": ts_code, "trade_date": trade_date}
                    )
                    conn.commit()
        
        df.to_sql('fact_index_daily', self.db_conn.engine, if_exists='append', index=False)
        return len(df)
    
    def get_last_trade_date(self, ts_code: str) -> Optional[str]:
        """获取指定指数的最后交易日期"""
        query = text("SELECT MAX(trade_date) FROM fact_index_daily WHERE ts_code = :ts_code")
        with self.db_conn.get_connection() as conn:
            result = conn.execute(query, {"ts_code": ts_code}).fetchone()
        return result[0] if result and result[0] else None
    
    def get_history_prices(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取历史行情数据"""
        query = "SELECT * FROM fact_index_daily WHERE ts_code = :ts_code"
        params = {"ts_code": ts_code}
        
        if start_date:
            query += " AND trade_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND trade_date <= :end_date"
            params["end_date"] = end_date
        
        query += " ORDER BY trade_date"
        return pd.read_sql(text(query), self.db_conn.engine, params=params)