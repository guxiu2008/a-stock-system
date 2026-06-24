#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股息率追踪器 数据库操作
使用 scripts.lib 中的共享表结构
"""

import pandas as pd
from typing import Optional
from scripts.lib import (
    FactDividendHistoryTable,
    DividendYieldTrackerLogTable,
    FactDailyQuotesTable,
    FactFinancialReportsTable,
)


class DividendYieldTrackerDatabase:
    """股息率追踪器数据库操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_path = db_path
        self.fact_dividend_history = FactDividendHistoryTable(db_path)
        self.dividend_yield_tracker_log = DividendYieldTrackerLogTable(db_path)
        self.fact_daily_quotes = FactDailyQuotesTable(db_path)
        self.fact_financial_reports = FactFinancialReportsTable(db_path)
    
    # ==================== 分红历史 ====================
    
    def save_dividend_history(self, df: pd.DataFrame) -> int:
        """保存分红历史数据"""
        return self.fact_dividend_history.save(df)
    
    def get_dividend_by_ts_code(self, ts_code: str) -> pd.DataFrame:
        """获取指定股票的分红数据"""
        return self.fact_dividend_history.get_by_ts_code(ts_code)
    
    def get_dividend_by_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取指定时间范围内的分红数据"""
        return self.fact_dividend_history.get_by_end_date(start_date, end_date)
    
    def get_all_dividends(self) -> pd.DataFrame:
        """获取所有分红数据"""
        return self.fact_dividend_history.get_all()
    
    def get_latest_dividend_year(self, ts_code: str) -> Optional[str]:
        """获取指定股票最新的分红年度"""
        return self.fact_dividend_history.get_latest_year(ts_code)
    
    def clear_dividend_history(self):
        """清空分红历史数据"""
        self.fact_dividend_history.clear()
    
    # ==================== 股价数据 ====================
    
    def get_latest_close_price(self, ts_code: str) -> Optional[float]:
        """
        获取指定股票最新的收盘价
        
        Args:
            ts_code: 股票代码
        
        Returns:
            最新收盘价，如果没有数据返回None
        """
        df = self.fact_daily_quotes.get_by_ts_code(ts_code)
        if not df.empty:
            df_sorted = df.sort_values('trade_date', ascending=False)
            return df_sorted.iloc[0]['close']
        return None
    
    # ==================== 财务数据 ====================
    
    def get_net_profit(self, ts_code: str, end_date: str) -> Optional[float]:
        """
        获取指定股票指定年度的净利润
        
        Args:
            ts_code: 股票代码
            end_date: 年度结束日期 (YYYYMMDD)
        
        Returns:
            净利润（元），如果没有数据返回None
        """
        df = self.fact_financial_reports.get(ts_code=ts_code, end_date=end_date)
        if not df.empty:
            return df.iloc[0]['net_profit']
        return None
    
    # ==================== 日志 ====================
    
    def log_update(self, data_type: str, record_count: int, status: str,
                   start_date: str = None, end_date: str = None):
        """记录更新日志"""
        self.dividend_yield_tracker_log.log(data_type, record_count, status, start_date, end_date)
    
    def get_last_update_time(self, data_type: str) -> Optional[str]:
        """获取最后更新时间"""
        return self.dividend_yield_tracker_log.get_last_update_time(data_type)