#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金流向表 (fact_money_flow) - 北向资金和融资融券数据
"""

from typing import Optional
import datetime
import pandas as pd
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class FactMoneyFlowTable:
    """资金流向表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS fact_money_flow (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT,
                    trade_date TEXT NOT NULL,
                    -- 北向资金相关字段
                    hsgt_net_amount REAL,
                    hgt_net_amount REAL,
                    sgt_net_amount REAL,
                    ggt_ss_net_amount REAL,
                    ggt_sz_net_amount REAL,
                    north_money REAL,
                    south_money REAL,
                    -- 全市场融资融券
                    exchange_id TEXT,
                    rzye_market REAL,
                    rzmre REAL,
                    rzche REAL,
                    rqye_market REAL,
                    rqmcl REAL,
                    rzrqye REAL,
                    rqyl REAL,
                    -- 个股融资融券
                    rzye REAL,
                    rqye REAL,
                    margin_ratio REAL,
                    rz_change_rate REAL,
                    update_time TEXT,
                    UNIQUE(ts_code, trade_date, exchange_id)
                )
            """))
            conn.commit()
    
    def save(self, df: pd.DataFrame) -> int:
        """保存资金流向数据"""
        if df.empty:
            return 0
        
        df['update_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 按数据类型分组处理
        for idx, row in df.iterrows():
            ts_code_val = row.get('ts_code')
            trade_date_val = row.get('trade_date')
            exchange_id_val = row.get('exchange_id')
            
            with self.db_conn.get_connection() as conn:
                # 构建删除条件
                delete_query = """
                    DELETE FROM fact_money_flow 
                    WHERE trade_date = :trade_date
                """
                params = {"trade_date": trade_date_val}
                
                # 添加ts_code条件
                if pd.notna(ts_code_val):
                    delete_query += " AND ts_code = :ts_code"
                    params["ts_code"] = ts_code_val
                else:
                    delete_query += " AND ts_code IS NULL"
                
                # 添加exchange_id条件
                if pd.notna(exchange_id_val):
                    delete_query += " AND exchange_id = :exchange_id"
                    params["exchange_id"] = exchange_id_val
                else:
                    delete_query += " AND exchange_id IS NULL"
                
                conn.execute(text(delete_query), params)
                conn.commit()
        
        df.to_sql('fact_money_flow', self.db_conn.engine, if_exists='append', index=False)
        return len(df)
    
    def get_hsgt_by_date(self, trade_date: str) -> Optional[pd.Series]:
        """获取指定日期的北向资金数据"""
        query = text("""
            SELECT * FROM fact_money_flow 
            WHERE ts_code IS NULL AND trade_date = :trade_date
            AND hsgt_net_amount IS NOT NULL
        """)
        with self.db_conn.get_connection() as conn:
            result = pd.read_sql(query, conn, params={"trade_date": trade_date})
        return result.iloc[0] if len(result) > 0 else None
    
    def get_margin_by_date(self, trade_date: str) -> Optional[pd.Series]:
        """获取指定日期的全市场融资融券数据"""
        query = text("""
            SELECT * FROM fact_money_flow 
            WHERE ts_code IS NULL AND trade_date = :trade_date
            AND rzye_market IS NOT NULL
        """)
        with self.db_conn.get_connection() as conn:
            result = pd.read_sql(query, conn, params={"trade_date": trade_date})
        return result.iloc[0] if len(result) > 0 else None
    
    def get_stock_margin(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取指定股票的融资融券明细"""
        query = "SELECT * FROM fact_money_flow WHERE ts_code = :ts_code"
        params = {"ts_code": ts_code}
        
        if start_date:
            query += " AND trade_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND trade_date <= :end_date"
            params["end_date"] = end_date
        
        query += " ORDER BY trade_date DESC"
        return pd.read_sql(text(query), self.db_conn.engine, params=params)
    
    def get_last_hsgt_date(self) -> Optional[str]:
        """获取北向资金数据的最后日期"""
        query = text("SELECT MAX(trade_date) FROM fact_money_flow WHERE hsgt_net_amount IS NOT NULL")
        with self.db_conn.get_connection() as conn:
            result = conn.execute(query).fetchone()
        return result[0] if result and result[0] else None
    
    def get_last_margin_date(self) -> Optional[str]:
        """获取融资融券数据的最后日期"""
        query = text("SELECT MAX(trade_date) FROM fact_money_flow WHERE rzye_market IS NOT NULL")
        with self.db_conn.get_connection() as conn:
            result = conn.execute(query).fetchone()
        return result[0] if result and result[0] else None
    
    def get_hsgt_history(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取北向资金历史数据"""
        query = "SELECT * FROM fact_money_flow WHERE ts_code IS NULL AND hsgt_net_amount IS NOT NULL"
        params = {}
        
        if start_date:
            query += " AND trade_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND trade_date <= :end_date"
            params["end_date"] = end_date
        
        query += " ORDER BY trade_date"
        return pd.read_sql(text(query), self.db_conn.engine, params=params)
    
    def get_margin_history(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取全市场融资融券历史数据"""
        query = "SELECT * FROM fact_money_flow WHERE ts_code IS NULL AND rzye_market IS NOT NULL"
        params = {}
        
        if start_date:
            query += " AND trade_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND trade_date <= :end_date"
            params["end_date"] = end_date
        
        query += " ORDER BY trade_date"
        return pd.read_sql(text(query), self.db_conn.engine, params=params)