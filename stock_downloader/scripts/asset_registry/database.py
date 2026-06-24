#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产注册表 数据库操作（向后兼容版本）
使用 scripts.lib 中的共享表结构
"""

import pandas as pd
from typing import Optional
from scripts.lib import (
    DimStockInfoTable,
    MapIndustryStockTable,
    MapConceptStockTable,
    DimTradeCalendarTable,
    AssetRegistryLogTable,
)


class AssetRegistryDatabase:
    """资产注册表数据库操作类（向后兼容）"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_path = db_path
        self.dim_stock_info = DimStockInfoTable(db_path)
        self.map_industry_stock = MapIndustryStockTable(db_path)
        self.map_concept_stock = MapConceptStockTable(db_path)
        self.dim_trade_calendar = DimTradeCalendarTable(db_path)
        self.asset_registry_log = AssetRegistryLogTable(db_path)
    
    # ==================== 股票基本信息 ====================
    
    def save_stock_basic(self, df: pd.DataFrame) -> int:
        """保存股票列表"""
        return self.dim_stock_info.save(df)
    
    def clear_stock_basic(self):
        """清空股票列表"""
        self.dim_stock_info.clear()
    
    def get_all_stocks(self) -> pd.DataFrame:
        """获取所有股票"""
        return self.dim_stock_info.get_all()
    
    def get_stock_info(self, ts_code: str = None, industry: str = None, 
                      market: str = None) -> pd.DataFrame:
        """获取股票信息（支持过滤）"""
        df = self.dim_stock_info.get_all()
        if ts_code:
            df = df[df['ts_code'] == ts_code]
        if industry:
            df = df[df['industry'] == industry]
        if market:
            df = df[df['market'] == market]
        return df
    
    # ==================== 行业分类 ====================
    
    def save_industry_classification(self, df: pd.DataFrame) -> int:
        """保存申万行业分类"""
        return self.map_industry_stock.save(df)
    
    def clear_industry_classification(self):
        """清空行业分类"""
        self.map_industry_stock.clear()
    
    def get_industry_classification(self) -> pd.DataFrame:
        """获取申万行业分类"""
        return self.map_industry_stock.get_all()
    
    def get_stocks_by_industry(self, industry_name: str) -> pd.DataFrame:
        """根据行业名称获取股票"""
        df = self.map_industry_stock.get_all()
        return df[df['industry_name'] == industry_name] if not df.empty else df
    
    def save_industry_classify(self, df: pd.DataFrame) -> int:
        """保存申万行业分类（兼容方法名）"""
        return self.save_industry_classification(df)
    
    # ==================== 概念分类 ====================
    
    def save_concept_classification(self, df: pd.DataFrame) -> int:
        """保存概念分类"""
        return self.map_concept_stock.save(df)
    
    def clear_concept_classification(self):
        """清空概念分类"""
        self.map_concept_stock.clear()
    
    def get_concept_classification(self) -> pd.DataFrame:
        """获取概念分类"""
        return self.map_concept_stock.get_all()
    
    def get_stocks_by_concept(self, concept_name: str) -> pd.DataFrame:
        """根据概念名称获取股票"""
        df = self.map_concept_stock.get_all()
        return df[df['concept_name'] == concept_name] if not df.empty else df
    
    def get_concepts_by_stock(self, ts_code: str) -> pd.DataFrame:
        """根据股票代码获取概念"""
        df = self.map_concept_stock.get_all()
        return df[df['ts_code'] == ts_code] if not df.empty else df
    
    def save_concept_classify(self, df: pd.DataFrame) -> int:
        """保存概念分类（兼容方法名）"""
        return self.save_concept_classification(df)
    
    # ==================== 交易日历 ====================
    
    def save_trade_calendar(self, df: pd.DataFrame) -> int:
        """保存交易日历"""
        return self.dim_trade_calendar.save(df)
    
    def clear_trade_calendar(self):
        """清空交易日历"""
        self.dim_trade_calendar.clear()
    
    def is_trading_day(self, date: str, exchange: str = 'SSE') -> bool:
        """判断是否为交易日"""
        return self.dim_trade_calendar.is_trading_day(date, exchange)
    
    # ==================== 日志 ====================
    
    def log_update(self, data_type: str, record_count: int, status: str):
        """记录更新日志"""
        self.asset_registry_log.log(data_type, record_count, status)
    
    def get_last_update_time(self, data_type: str) -> Optional[str]:
        """获取最后更新时间"""
        return self.asset_registry_log.get_last_update_time(data_type)