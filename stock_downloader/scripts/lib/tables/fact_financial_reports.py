#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务报告表 (fact_financial_reports)
"""

import pandas as pd
from sqlalchemy import text
from scripts.lib.base import DatabaseConnection


class FactFinancialReportsTable:
    """财务报告表操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_conn = DatabaseConnection(db_path)
        self._init_table()
    
    def _init_table(self):
        """初始化表结构"""
        with self.db_conn.get_connection() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS fact_financial_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_code TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    ann_date TEXT,
                    report_type TEXT,
                    money_cap REAL,
                    accounts_receiv REAL,
                    total_assets REAL,
                    total_liab REAL,
                    revenue REAL,
                    net_profit REAL,
                    kcfjce REAL,
                    ncf_from_oa REAL,
                    roe REAL,
                    roe_waa REAL,
                    roe_dt REAL,
                    grossprofit_margin REAL,
                    netprofit_margin REAL,
                    debt_to_assets REAL,
                    update_flag TEXT,
                    update_time TEXT,
                    UNIQUE(ts_code, end_date)
                )
            """))
            # 添加索引以提高查询性能
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fr_ts_code ON fact_financial_reports(ts_code)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fr_end_date ON fact_financial_reports(end_date)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fr_ts_end ON fact_financial_reports(ts_code, end_date)"))
            conn.commit()
    
    def save(self, df: pd.DataFrame) -> int:
        """保存财务报告数据（批量操作优化，不使用临时表）"""
        if df.empty:
            return 0
        
        saved_count = 0
        
        # 确保有必要的列
        if 'ts_code' not in df.columns or 'end_date' not in df.columns:
            print("错误：数据缺少 ts_code 或 end_date 列")
            return 0
        
        with self.db_conn.get_connection() as conn:
            # 第一步：批量查询已存在的记录
            ts_end_pairs = list(df[['ts_code', 'end_date']].itertuples(index=False, name=None))
            
            # SQLite 不支持 (a,b) IN ((x,y),(z,w)) 语法，改用 OR 条件或分两次查询
            # 先查询所有已存在的记录
            existing_query = text("""
                SELECT ts_code, end_date FROM fact_financial_reports
            """)
            all_existing = set(conn.execute(existing_query).fetchall())
            
            # 然后找出在新数据中且已存在的记录
            existing = set()
            for pair in ts_end_pairs:
                if pair in all_existing:
                    existing.add(pair)
            
            # 第二步：将数据分成需要更新和需要插入的两部分
            df['exists'] = df.apply(lambda x: (x['ts_code'], x['end_date']) in existing, axis=1)
            df_to_update = df[df['exists']].copy()
            df_to_insert = df[~df['exists']].copy()
            
            # 第三步：批量插入新记录
            if not df_to_insert.empty:
                # 移除 exists 列后插入
                df_to_insert = df_to_insert.drop(columns=['exists'])
                df_to_insert.to_sql('fact_financial_reports', conn, if_exists='append', index=False)
                saved_count += len(df_to_insert)
            
            # 第四步：批量更新已存在的记录
            if not df_to_update.empty:
                df_to_update = df_to_update.drop(columns=['exists'])
                
                # 定义所有可能的列
                all_columns = [
                    'ann_date', 'report_type', 'money_cap', 'accounts_receiv',
                    'total_assets', 'total_liab', 'revenue', 'net_profit', 'kcfjce',
                    'ncf_from_oa', 'roe', 'roe_waa', 'roe_dt', 'grossprofit_margin',
                    'netprofit_margin', 'debt_to_assets', 'update_flag', 'update_time'
                ]
                
                # 只使用 DataFrame 中实际存在的列
                update_columns = [col for col in all_columns if col in df_to_update.columns]
                
                if update_columns:
                    # 构建 UPDATE 语句，使用 COALESCE 保留非空值
                    set_clause = ', '.join([f"{col} = COALESCE(:{col}, {col})" for col in update_columns])
                    update_query = text(f"""
                        UPDATE fact_financial_reports 
                        SET {set_clause}
                        WHERE ts_code = :ts_code AND end_date = :end_date
                    """)
                    
                    # 批量执行更新
                    update_data = df_to_update.to_dict('records')
                    result = conn.execute(update_query, update_data)
                    saved_count += result.rowcount
            
            conn.commit()
        
        return saved_count
    
    def get(self, ts_code: str = None, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """查询财务报告"""
        query = "SELECT * FROM fact_financial_reports WHERE 1=1"
        params = {}
        
        if ts_code:
            query += " AND ts_code = :ts_code"
            params["ts_code"] = ts_code
        if start_date:
            query += " AND end_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND end_date <= :end_date"
            params["end_date"] = end_date
        
        query += " ORDER BY ts_code, end_date DESC"
        return pd.read_sql(text(query), self.db_conn.engine, params=params)