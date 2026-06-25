#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务护城河 数据库操作（向后兼容版本）
使用 scripts.lib 中的共享表结构
"""

import pandas as pd
from typing import Optional
from scripts.lib import (
    DimStockInfoTable,
    FactFinancialReportsTable,
    FactRevenueSegmentsTable,
    FundamentalMasterLogTable,
)


class FundamentalDatabase:
    """财务护城河数据库操作类（向后兼容）"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_path = db_path
        self.dim_stock_info = DimStockInfoTable(db_path)
        self.fact_financial_reports = FactFinancialReportsTable(db_path)
        self.fact_revenue_segments = FactRevenueSegmentsTable(db_path)
        self.fundamental_master_log = FundamentalMasterLogTable(db_path)
    
    # ==================== 股票基本信息 ====================
    
    def get_all_stocks(self) -> pd.DataFrame:
        """获取所有股票"""
        return self.dim_stock_info.get_all()
    
    # ==================== 财务报告 ====================
    
    def save_financial_report(self, df: pd.DataFrame) -> int:
        """保存财务报告数据（更新或插入）"""
        return self.fact_financial_reports.save(df)
    
    def save_financial_reports(self, df: pd.DataFrame) -> int:
        """保存财务报告数据（更新或插入）- 别名"""
        return self.save_financial_report(df)
    
    def get_financial_reports(self, ts_code: str = None, 
                           start_date: str = None, 
                           end_date: str = None) -> pd.DataFrame:
        """查询财务报告"""
        return self.fact_financial_reports.get(ts_code, start_date, end_date)
    
    def get_existing_periods(self) -> set:
        """
        获取数据库中已存在的 (ts_code, end_date) 组合
        
        Returns:
            集合，每个元素是 (ts_code, end_date) 元组
        """
        from sqlalchemy import text
        with self.fact_financial_reports.db_conn.get_connection() as conn:
            result = conn.execute(text("SELECT ts_code, end_date FROM fact_financial_reports"))
            return set((row[0], row[1]) for row in result)
    
    def get_existing_by_period(self, period: str) -> set:
        """
        获取指定报告期已存在的股票
        
        Args:
            period: 报告期，如 '20231231'
            
        Returns:
            已存在该报告期数据的股票代码集合
        """
        from sqlalchemy import text
        with self.fact_financial_reports.db_conn.get_connection() as conn:
            result = conn.execute(
                text("SELECT ts_code FROM fact_financial_reports WHERE end_date = :end_date"),
                {"end_date": period}
            )
            return set(row[0] for row in result)
    
    def filter_need_update(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤出需要更新的记录
        
        逻辑：
        1. 数据库中不存在的记录，需要插入
        2. 数据库中存在但 update_flag 为 '1' 的记录，需要更新
        
        Args:
            df: 新获取的财务数据DataFrame
            
        Returns:
            需要更新的DataFrame
        """
        if df.empty:
            return df
        
        # 获取已存在的记录
        existing = self.get_existing_periods()
        
        # 标记哪些记录需要处理
        def need_update(row):
            key = (row['ts_code'], row['end_date'])
            if key not in existing:
                return True  # 新记录，需要插入
            # 已存在的记录，检查 update_flag
            if 'update_flag' in row and row['update_flag'] == '1':
                return True  # 有更新标记，需要更新
            return False  # 无需更新
        
        df_filtered = df[df.apply(need_update, axis=1)].copy()
        
        if len(df_filtered) < len(df):
            print(f"  过滤掉 {len(df) - len(df_filtered)} 条无需更新的记录")
        
        return df_filtered
    
    # ==================== 日志 ====================
    
    def log_update(self, data_type: str, record_count: int, status: str, 
                   start_date: str = None, end_date: str = None):
        """记录更新日志"""
        self.fundamental_master_log.log(data_type, record_count, status, 
                                         start_date, end_date)
    
    def get_last_update_time(self, data_type: str) -> Optional[str]:
        """获取最后更新时间"""
        return self.fundamental_master_log.get_last_update_time(data_type)

    # ==================== 主营业务构成 ====================

    def save_revenue_segments(self, df: pd.DataFrame) -> int:
        """保存主营业务构成数据"""
        return self.fact_revenue_segments.save(df)

    def get_revenue_segments(self, ts_code: str = None, end_date: str = None,
                             bz_type: str = None) -> pd.DataFrame:
        """查询主营业务构成"""
        return self.fact_revenue_segments.get(ts_code, end_date, bz_type)

    def get_existing_segments_by_period(self, period: str) -> set:
        """获取指定报告期已有主营业务构成数据的股票代码集合"""
        return self.fact_revenue_segments.get_existing_by_period(period)