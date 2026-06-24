#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金流向分析 数据库操作
"""

import pandas as pd
from typing import Optional
from scripts.lib import (
    FactMoneyFlowTable,
    MoneyFlowAnalystLogTable,
)


class MoneyFlowAnalystDatabase:
    """资金流向分析数据库操作类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_path = db_path
        self.fact_money_flow = FactMoneyFlowTable(db_path)
        self.money_flow_log = MoneyFlowAnalystLogTable(db_path)
    
    # ==================== 北向资金 ====================
    
    def save_hsgt(self, df: pd.DataFrame) -> int:
        """保存北向资金数据"""
        if df.empty:
            return 0
        # 确保ts_code为NULL表示全市场数据
        df = df.copy()
        if 'ts_code' not in df.columns:
            df['ts_code'] = None
        return self.fact_money_flow.save(df)
    
    def get_hsgt_by_date(self, trade_date: str) -> Optional[pd.Series]:
        """获取指定日期的北向资金数据"""
        return self.fact_money_flow.get_hsgt_by_date(trade_date)
    
    def get_hsgt_history(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取北向资金历史数据"""
        return self.fact_money_flow.get_hsgt_history(start_date, end_date)
    
    def get_last_hsgt_date(self) -> Optional[str]:
        """获取北向资金数据的最后日期"""
        return self.fact_money_flow.get_last_hsgt_date()
    
    # ==================== 全市场融资融券 ====================
    
    def save_market_margin(self, df: pd.DataFrame) -> int:
        """保存全市场融资融券数据"""
        if df.empty:
            return 0
        df = df.copy()
        if 'ts_code' not in df.columns:
            df['ts_code'] = None
        return self.fact_money_flow.save(df)
    
    def get_margin_by_date(self, trade_date: str) -> Optional[pd.Series]:
        """获取指定日期的全市场融资融券数据"""
        return self.fact_money_flow.get_margin_by_date(trade_date)
    
    def get_margin_history(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取全市场融资融券历史数据"""
        return self.fact_money_flow.get_margin_history(start_date, end_date)
    
    def get_last_margin_date(self) -> Optional[str]:
        """获取融资融券数据的最后日期"""
        return self.fact_money_flow.get_last_margin_date()
    
    # ==================== 个股融资融券 ====================
    
    def save_stock_margin(self, df: pd.DataFrame) -> int:
        """保存个股融资融券明细"""
        return self.fact_money_flow.save(df)
    
    def get_stock_margin(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取指定股票的融资融券明细"""
        return self.fact_money_flow.get_stock_margin(ts_code, start_date, end_date)
    
    # ==================== 日志 ====================
    
    def log_start(self, action_type: str, data_type: str = None, start_date: str = None, end_date: str = None) -> int:
        """记录开始日志"""
        return self.money_flow_log.log_start(action_type, data_type, start_date, end_date)
    
    def log_success(self, log_id: int, record_count: int = 0):
        """记录成功日志"""
        self.money_flow_log.log_success(log_id, record_count)
    
    def log_error(self, log_id: int, error_msg: str):
        """记录错误日志"""
        self.money_flow_log.log_error(log_id, error_msg)
    
    def get_last_update_time(self, action_type: str) -> Optional[str]:
        """获取最后更新时间"""
        return self.money_flow_log.get_last_update_time(action_type)