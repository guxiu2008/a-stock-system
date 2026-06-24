#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票基础信息表 (dim_stock_info)
"""

import pandas as pd
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class DimStockInfoTable:
    """股票基础信息表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dim_stock_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL UNIQUE,
                    symbol TEXT,
                    name TEXT,
                    area TEXT,
                    industry TEXT,
                    fullname TEXT,
                    enname TEXT,
                    market TEXT,
                    exchange TEXT,
                    curr_type TEXT,
                    list_status TEXT,
                    list_date TEXT,
                    delist_date TEXT,
                    is_hs TEXT,
                    update_time TEXT,
                    UNIQUE(ts_code)
                )
            """))
            conn.commit()
    
    def save(self, df: pd.DataFrame) -> int:
        """保存股票基础信息（全量替换）"""
        if df.empty:
            return 0
        
        with self.db_conn.get_connection() as conn:
            conn.execute(text("DELETE FROM dim_stock_info"))
            conn.commit()
        
        df.to_sql('dim_stock_info', self.db_conn.engine, if_exists='append', index=False)
        return len(df)
    
    def get(self, ts_code: str = None, industry: str = None, market: str = None) -> pd.DataFrame:
        """查询股票信息"""
        query = "SELECT * FROM dim_stock_info WHERE 1=1"
        params = {}
        
        if ts_code:
            query += " AND ts_code = :ts_code"
            params["ts_code"] = ts_code
        if industry:
            query += " AND industry = :industry"
            params["industry"] = industry
        if market:
            query += " AND market = :market"
            params["market"] = market
        
        query += " ORDER BY ts_code"
        return pd.read_sql(text(query), self.db_conn.engine, params=params)