#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行业分类表 (map_industry_stock)
"""

import pandas as pd
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class MapIndustryStockTable:
    """行业分类表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS map_industry_stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    industry_type TEXT NOT NULL,
                    industry_code TEXT,
                    industry_name TEXT,
                    update_time TEXT,
                    UNIQUE(ts_code, industry_type)
                )
            """))
            conn.commit()
    
    def save(self, df: pd.DataFrame) -> int:
        """保存行业分类信息（全量替换）"""
        if df.empty:
            return 0
        
        with self.db_conn.get_connection() as conn:
            conn.execute(text("DROP TABLE IF EXISTS map_industry_stock"))
            conn.execute(text("""
                CREATE TABLE map_industry_stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    industry_type TEXT NOT NULL,
                    industry_code TEXT,
                    industry_name TEXT,
                    update_time TEXT,
                    UNIQUE(ts_code, industry_code)
                )
            """))
            conn.commit()
        
        df.to_sql('map_industry_stock', self.db_conn.engine, if_exists='append', index=False)
        return len(df)