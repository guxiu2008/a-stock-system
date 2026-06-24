#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行情同步器 数据库操作（向后兼容版本）
使用 scripts.lib 中的共享表结构
"""

import pandas as pd
from typing import Optional, Tuple
from scripts.lib import (
    DimStockInfoTable,
    FactDailyQuotesTable,
    FactIndexDailyTable,
    StockSyncStatusTable,
    IndexSyncStatusTable,
    MarketIndicatorsTable,
    MarketQuotaLogTable,
)


class MarketDatabase:
    """行情数据库操作类（向后兼容）"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_path = db_path
        self.dim_stock_info = DimStockInfoTable(db_path)
        self.fact_daily_quotes = FactDailyQuotesTable(db_path)
        self.fact_index_daily = FactIndexDailyTable(db_path)
        self.stock_sync_status = StockSyncStatusTable(db_path)
        self.index_sync_status = IndexSyncStatusTable(db_path)
        self.market_indicators = MarketIndicatorsTable(db_path)
        self.market_quota_log = MarketQuotaLogTable(db_path)
    
    # ==================== 股票基本信息 ====================
    
    def get_all_stocks(self) -> pd.DataFrame:
        """获取所有股票"""
        return self.dim_stock_info.get_all()
    
    # ==================== 个股日线行情 ====================
    
    def save_daily_quotes(self, df: pd.DataFrame) -> int:
        """保存个股日线行情数据"""
        return self.fact_daily_quotes.save(df)
    
    def get_last_trade_date(self, ts_code: str, is_index: bool = False) -> Optional[str]:
        """获取指定股票/指数的最后交易日期"""
        if is_index:
            return self.fact_index_daily.get_last_trade_date(ts_code)
        return self.fact_daily_quotes.get_last_trade_date(ts_code)
    
    def get_history_prices(self, ts_code: str, 
                          start_date: str = None, 
                          end_date: str = None,
                          is_index: bool = False) -> pd.DataFrame:
        """获取历史行情数据"""
        if is_index:
            return self.fact_index_daily.get_history_prices(ts_code, start_date, end_date)
        return self.fact_daily_quotes.get_history_prices(ts_code, start_date, end_date)
    
    # ==================== 指数日线行情 ====================
    
    def save_index_daily(self, df: pd.DataFrame) -> int:
        """保存指数日线行情数据"""
        return self.fact_index_daily.save(df)
    
    def get_index_last_trade_date(self, ts_code: str) -> Optional[str]:
        """获取指定指数的最后交易日期"""
        return self.fact_index_daily.get_last_trade_date(ts_code)
    
    def get_index_history_prices(self, ts_code: str, 
                                 start_date: str = None, 
                                 end_date: str = None) -> pd.DataFrame:
        """获取指数历史行情数据"""
        return self.fact_index_daily.get_history_prices(ts_code, start_date, end_date)
    
    # ==================== 股票同步状态 ====================
    
    def get_sync_status(self, ts_code: str) -> Optional[dict]:
        """获取股票同步状态"""
        return self.stock_sync_status.get(ts_code)
    
    def update_sync_status(self, ts_code: str, last_sync_date: str, 
                          sync_status: str = 'success'):
        """更新股票同步状态"""
        self.stock_sync_status.update(ts_code, last_sync_date, sync_status)
    
    def update_stock_sync_status(self, ts_code: str, last_sync_date: str, 
                                 sync_status: str = 'success'):
        """更新股票同步状态"""
        self.stock_sync_status.update(ts_code, last_sync_date, sync_status)
    
    def get_all_sync_status(self, is_index: bool = False) -> pd.DataFrame:
        """获取所有股票/指数的同步状态"""
        if is_index:
            return self.index_sync_status.get_all()
        return self.stock_sync_status.get_all()
    
    # ==================== 指数同步状态 ====================
    
    def get_index_sync_status(self, ts_code: str) -> Optional[dict]:
        """获取指数同步状态"""
        return self.index_sync_status.get(ts_code)
    
    def update_index_sync_status(self, ts_code: str, last_sync_date: str, 
                                sync_status: str = 'success'):
        """更新指数同步状态"""
        self.index_sync_status.update(ts_code, last_sync_date, sync_status)
    
    # ==================== 技术指标 ====================
    
    def delete_indicators(self, ts_code: str):
        """删除指定股票的所有技术指标"""
        self.market_indicators.delete_by_ts_code(ts_code)
    
    def delete_indicators_by_ts_code(self, ts_code: str):
        """删除指定股票的所有技术指标（别名）"""
        self.market_indicators.delete_by_ts_code(ts_code)
    
    def save_indicators(self, df: pd.DataFrame):
        """保存技术指标数据"""
        self.market_indicators.save(df)
    
    def get_indicators(self, ts_code: str, 
                      start_date: str = None, 
                      end_date: str = None) -> pd.DataFrame:
        """获取技术指标数据"""
        return self.market_indicators.get(ts_code, start_date, end_date)
    
    # ==================== 日志 ====================
    
    def log_sync(self, sync_type: str, ts_code: str, 
                start_date: str, end_date: str, 
                record_count: int, status: str):
        """记录同步日志"""
        self.market_quota_log.log(sync_type, ts_code, start_date, end_date, record_count, status)
    
    def calculate_drawdown(self, ts_code: str, window: int = 252, is_index: bool = False) -> Tuple[float, pd.DataFrame]:
        """计算最大回撤"""
        df = self.get_history_prices(ts_code, is_index=is_index)
        if df.empty or 'close' not in df.columns:
            return 0.0, pd.DataFrame()
        
        df = df.sort_values('trade_date', ascending=True).copy()
        df['cummax'] = df['close'].rolling(window=window, min_periods=1).max()
        df['drawdown'] = (df['close'] - df['cummax']) / df['cummax']
        max_drawdown = df['drawdown'].min()
        return abs(max_drawdown) * 100, df
    
    def detect_volume_surge(self, ts_code: str, short_window: int = 5, long_window: int = 20) -> Tuple[bool, float]:
        """检测成交量放量"""
        df = self.get_history_prices(ts_code)
        if df.empty or 'vol' not in df.columns:
            return False, 0.0
        
        df = df.sort_values('trade_date', ascending=True).copy()
        df['vol_short_mean'] = df['vol'].rolling(window=short_window).mean()
        df['vol_long_mean'] = df['vol'].rolling(window=long_window).mean()
        
        if len(df) < long_window:
            return False, 0.0
        
        latest_ratio = df.iloc[-1]['vol_short_mean'] / df.iloc[-1]['vol_long_mean'] if df.iloc[-1]['vol_long_mean'] > 0 else 0
        return latest_ratio > 2.0, latest_ratio
