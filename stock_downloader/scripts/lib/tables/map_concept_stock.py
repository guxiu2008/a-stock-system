#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
概念分类表 (map_concept_stock)
"""

import pandas as pd
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class MapConceptStockTable:
    """概念分类表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS map_concept_stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    concept_code TEXT,
                    concept_name TEXT,
                    in_date TEXT,
                    out_date TEXT,
                    update_time TEXT,
                    UNIQUE(ts_code, concept_code)
                )
            """))
            conn.commit()
    
    def save(self, df: pd.DataFrame) -> int:
        """保存概念分类信息（全量替换）"""
        if df.empty:
            return 0
        
        with self.db_conn.get_connection() as conn:
            conn.execute(text("DROP TABLE IF EXISTS map_concept_stock"))
            conn.execute(text("""
                CREATE TABLE map_concept_stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    concept_code TEXT,
                    concept_name TEXT,
                    update_time TEXT,
                    UNIQUE(ts_code, concept_code)
                )
            """))
            conn.commit()
        
        df.to_sql('map_concept_stock', self.db_conn.engine, if_exists='append', index=False)
        return len(df)