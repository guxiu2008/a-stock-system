#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术指标表 (market_indicators)
"""

import pandas as pd
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class MarketIndicatorsTable:
    """技术指标表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS market_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    trade_date TEXT NOT NULL,
                    ma5 REAL,
                    ma10 REAL,
                    ma20 REAL,
                    ma30 REAL,
                    ma60 REAL,
                    ma120 REAL,
                    macd REAL,
                    macd_signal REAL,
                    macd_hist REAL,
                    kdj_k REAL,
                    kdj_d REAL,
                    kdj_j REAL,
                    rsi6 REAL,
                    rsi12 REAL,
                    rsi24 REAL,
                    boll_upper REAL,
                    boll_mid REAL,
                    boll_lower REAL,
                    UNIQUE(ts_code, trade_date)
                )
            """))
            conn.commit()
    
    def delete_by_ts_code(self, ts_code: str):
        """删除指定股票的所有技术指标"""
        with self.db_conn.get_connection() as conn:
            conn.execute(
                text("DELETE FROM market_indicators WHERE ts_code = :ts_code"),
                {"ts_code": ts_code}
            )
            conn.commit()
    
    def save(self, df: pd.DataFrame):
        """保存技术指标数据"""
        if df.empty:
            return
        
        ts_codes = df['ts_code'].unique()
        for ts_code in ts_codes:
            self.delete_by_ts_code(ts_code)
        
        df.to_sql('market_indicators', self.db_conn.engine, if_exists='append', index=False)
    
    def get(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取技术指标数据"""
        query = "SELECT * FROM market_indicators WHERE ts_code = :ts_code"
        params = {"ts_code": ts_code}
        
        if start_date:
            query += " AND trade_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND trade_date <= :end_date"
            params["end_date"] = end_date
        
        query += " ORDER BY trade_date"
        return pd.read_sql(text(query), self.db_conn.engine, params=params)