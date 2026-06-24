#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产注册表 - 主类
"""

from typing import Optional

import pandas as pd

from .database import AssetRegistryDatabase as AssetRegistryDB
from .fetcher import DataFetcher


class AssetRegistry:
    """资产注册表主类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        """
        初始化资产注册表
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db = AssetRegistryDB(db_path)
        self.fetcher = None
    
    def _ensure_fetcher(self):
        """确保数据获取器已初始化"""
        if self.fetcher is None:
            self.fetcher = DataFetcher()
    
    def update_stock_basic(self) -> int:
        """
        更新股票基础信息
        
        Returns:
            更新的记录数
        """
        self._ensure_fetcher()
        
        df = self.fetcher.fetch_stock_basic()
        if df.empty:
            return 0
        
        count = self.db.save_stock_basic(df)
        self.db.log_update('stock_basic', count, 'success')
        
        print(f"股票基础信息更新完成，共 {count} 条记录")
        return count
    
    def update_industry_classify(self) -> int:
        """
        更新申万行业分类
        
        Returns:
            更新的记录数
        """
        self._ensure_fetcher()
        
        df = self.fetcher.fetch_industry_classify()
        if df.empty:
            return 0
        
        count = self.db.save_industry_classify(df)
        self.db.log_update('industry_classify', count, 'success')
        
        print(f"申万行业分类更新完成，共 {count} 条记录")
        return count
    
    def update_trade_calendar(self, start_date: str = None, end_date: str = None) -> int:
        """
        更新交易日历
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            更新的记录数
        """
        self._ensure_fetcher()
        
        df_sse, df_szse = self.fetcher.fetch_trade_calendar(start_date, end_date)
        
        total_count = 0
        
        if not df_sse.empty:
            self.db.clear_trade_calendar()
            count = self.db.save_trade_calendar(df_sse)
            total_count += count
        
        if not df_szse.empty:
            count = self.db.save_trade_calendar(df_szse)
            total_count += count
        
        if total_count > 0:
            self.db.log_update('trade_calendar', total_count, 'success')
            print(f"交易日历更新完成，共 {total_count} 条记录")
        
        return total_count
    
    def update_concept_classify(self) -> int:
        """
        更新概念分类
        
        Returns:
            更新的记录数
        """
        self._ensure_fetcher()
        
        df = self.fetcher.fetch_concept_classify()
        if df.empty:
            return 0
        
        count = self.db.save_concept_classify(df)
        self.db.log_update('concept_classify', count, 'success')
        
        print(f"概念分类更新完成，共 {count} 条记录")
        return count
    
    def update_all(self):
        """更新所有数据"""
        print("=" * 60)
        print("开始更新资产注册表")
        print("=" * 60)
        
        try:
            self.update_stock_basic()
        except Exception as e:
            print(f"更新股票基础信息失败: {e}")
        
        try:
            self.update_industry_classify()
        except Exception as e:
            print(f"更新行业分类失败: {e}")
        
        try:
            self.update_concept_classify()
        except Exception as e:
            print(f"更新概念分类失败: {e}")
        
        try:
            self.update_trade_calendar()
        except Exception as e:
            print(f"更新交易日历失败: {e}")
        
        print("=" * 60)
        print("资产注册表更新完成")
        print("=" * 60)
    
    # 代理方法 - 直接调用数据库方法
    def get_stock_info(self, ts_code: str = None, industry: str = None, 
                      market: str = None) -> pd.DataFrame:
        return self.db.get_stock_info(ts_code, industry, market)
    
    def get_stocks_by_industry(self, industry_name: str) -> pd.DataFrame:
        return self.db.get_stocks_by_industry(industry_name)
    
    def get_stocks_by_concept(self, concept_name: str) -> pd.DataFrame:
        return self.db.get_stocks_by_concept(concept_name)
    
    def get_concepts_by_stock(self, ts_code: str) -> pd.DataFrame:
        return self.db.get_concepts_by_stock(ts_code)
    
    def is_trading_day(self, date: str, exchange: str = 'SSE') -> bool:
        return self.db.is_trading_day(date, exchange)
    
    def get_last_update_time(self, data_type: str) -> Optional[str]:
        return self.db.get_last_update_time(data_type)
