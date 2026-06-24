#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金流向分析 - 主类
"""

import datetime
from typing import Optional

import pandas as pd

from .database import MoneyFlowAnalystDatabase as MoneyFlowDB
from .fetcher import MoneyFlowDataFetcher


class MoneyFlowAnalyst:
    """资金流向分析主类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        """
        初始化资金流向分析
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db = MoneyFlowDB(db_path)
        self.fetcher = None
    
    def _ensure_fetcher(self):
        """确保数据获取器已初始化"""
        if self.fetcher is None:
            self.fetcher = MoneyFlowDataFetcher()
    
    def _get_date_range(self, last_date: Optional[str], days: int = 30) -> tuple:
        """
        获取需要更新的日期范围
        
        Args:
            last_date: 数据库中已有的最后日期
            days: 默认获取的天数
        
        Returns:
            (start_date, end_date)
        """
        today = datetime.datetime.now()
        end_date = today.strftime('%Y%m%d')
        
        if last_date:
            # 从最后日期的下一天开始
            last_dt = datetime.datetime.strptime(last_date, '%Y%m%d')
            start_dt = last_dt + datetime.timedelta(days=1)
            start_date = start_dt.strftime('%Y%m%d')
        else:
            # 没有历史数据，获取指定天数
            start_dt = today - datetime.timedelta(days=days)
            start_date = start_dt.strftime('%Y%m%d')
        
        return start_date, end_date
    
    def update_hsgt(self, start_date: str = None, end_date: str = None, force: bool = False) -> int:
        """
        更新北向资金数据
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            force: 是否强制更新，忽略已有数据
        
        Returns:
            更新的记录数
        """
        self._ensure_fetcher()
        
        log_id = self.db.log_start('update', 'hsgt', start_date, end_date)
        
        try:
            if not force and not start_date and not end_date:
                # 增量更新模式
                last_date = self.db.get_last_hsgt_date()
                start_date, end_date = self._get_date_range(last_date, days=365)
                
                # 使用datetime对象比较日期，避免字符串比较的潜在问题
                start_dt = datetime.datetime.strptime(start_date, '%Y%m%d')
                end_dt = datetime.datetime.strptime(end_date, '%Y%m%d')
                if start_dt > end_dt:
                    print("北向资金数据已是最新，无需更新")
                    self.db.log_success(log_id, 0)
                    return 0
            
            df = self.fetcher.fetch_hsgt(start_date=start_date, end_date=end_date)
            if df.empty:
                print("未获取到北向资金数据")
                self.db.log_success(log_id, 0)
                return 0
            
            # 按日期分批保存，避免内存占用过大
            count = 0
            for trade_date in df['trade_date'].unique():
                df_date = df[df['trade_date'] == trade_date].copy()
                # 先检查是否已存在
                existing = self.db.get_hsgt_by_date(trade_date)
                if existing is not None and not force:
                    continue
                # 保存数据
                cnt = self.db.save_hsgt(df_date)
                count += cnt
            
            self.db.log_success(log_id, count)
            print(f"北向资金数据更新完成，共 {count} 条记录")
            return count
            
        except Exception as e:
            error_msg = str(e)
            print(f"更新北向资金数据失败: {error_msg}")
            self.db.log_error(log_id, error_msg)
            return 0
    
    def update_market_margin(self, start_date: str = None, end_date: str = None, force: bool = False) -> int:
        """
        更新全市场融资融券数据
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            force: 是否强制更新
        
        Returns:
            更新的记录数
        """
        self._ensure_fetcher()
        
        log_id = self.db.log_start('update', 'market_margin', start_date, end_date)
        
        try:
            if not force and not start_date and not end_date:
                # 增量更新模式
                last_date = self.db.get_last_margin_date()
                start_date, end_date = self._get_date_range(last_date, days=365)
                
                # 使用datetime对象比较日期，避免字符串比较的潜在问题
                start_dt = datetime.datetime.strptime(start_date, '%Y%m%d')
                end_dt = datetime.datetime.strptime(end_date, '%Y%m%d')
                if start_dt > end_dt:
                    print("全市场融资融券数据已是最新，无需更新")
                    self.db.log_success(log_id, 0)
                    return 0
            
            df = self.fetcher.fetch_margin(start_date=start_date, end_date=end_date)
            if df.empty:
                print("未获取到全市场融资融券数据")
                self.db.log_success(log_id, 0)
                return 0
            
            count = 0
            for trade_date in df['trade_date'].unique():
                df_date = df[df['trade_date'] == trade_date].copy()
                existing = self.db.get_margin_by_date(trade_date)
                if existing is not None and not force:
                    continue
                cnt = self.db.save_market_margin(df_date)
                count += cnt
            
            self.db.log_success(log_id, count)
            print(f"全市场融资融券数据更新完成，共 {count} 条记录")
            return count
            
        except Exception as e:
            error_msg = str(e)
            print(f"更新全市场融资融券数据失败: {error_msg}")
            self.db.log_error(log_id, error_msg)
            return 0
    
    def update_stock_margin_by_date(self, trade_date: str, force: bool = False) -> int:
        """
        更新指定日期的个股融资融券明细
        
        Args:
            trade_date: 交易日 (YYYYMMDD)
            force: 是否强制更新
        
        Returns:
            更新的记录数
        """
        self._ensure_fetcher()
        
        log_id = self.db.log_start('update', 'stock_margin', trade_date, trade_date)
        
        try:
            # 检查是否已存在
            # 获取数据库中该日期的数据量
            existing_df = self.db.get_stock_margin('', trade_date, trade_date)
            if len(existing_df) > 0 and not force:
                print(f"{trade_date} 的个股融资融券明细已存在，跳过更新")
                self.db.log_success(log_id, 0)
                return 0
            
            df = self.fetcher.fetch_margin_detail(trade_date=trade_date)
            if df.empty:
                print(f"未获取到 {trade_date} 的个股融资融券明细")
                self.db.log_success(log_id, 0)
                return 0
            
            count = self.db.save_stock_margin(df)
            
            self.db.log_success(log_id, count)
            print(f"{trade_date} 个股融资融券明细更新完成，共 {count} 条记录")
            return count
            
        except Exception as e:
            error_msg = str(e)
            print(f"更新个股融资融券明细失败: {error_msg}")
            self.db.log_error(log_id, error_msg)
            return 0
    
    def update_all(self, update_stock_margin: bool = False):
        """
        更新所有资金流向数据
        
        Args:
            update_stock_margin: 是否更新个股融资融券明细（数据量大，默认不更新）
        """
        print("=" * 60)
        print("开始更新资金流向数据")
        print("=" * 60)
        
        try:
            self.update_hsgt()
        except Exception as e:
            print(f"更新北向资金数据失败: {e}")
        
        try:
            self.update_market_margin()
        except Exception as e:
            print(f"更新全市场融资融券数据失败: {e}")
        
        if update_stock_margin:
            try:
                # 获取最近的交易日
                end_date = datetime.datetime.now().strftime('%Y%m%d')
                self.update_stock_margin_by_date(end_date)
            except Exception as e:
                print(f"更新个股融资融券明细失败: {e}")
        
        print("=" * 60)
        print("资金流向数据更新完成")
        print("=" * 60)
    
    # ==================== 分析方法 ====================
    
    def analyze_hsgt_trend(self, days: int = 30) -> pd.DataFrame:
        """
        分析北向资金趋势
        
        Args:
            days: 分析天数
        
        Returns:
            趋势分析DataFrame
        """
        end_date = datetime.datetime.now().strftime('%Y%m%d')
        start_dt = datetime.datetime.now() - datetime.timedelta(days=days)
        start_date = start_dt.strftime('%Y%m%d')
        
        df = self.db.get_hsgt_history(start_date, end_date)
        if df.empty:
            return pd.DataFrame()
        
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        df = df.sort_values('trade_date')
        
        # 计算均值
        df['hsgt_ma5'] = df['hsgt_net_amount'].rolling(5).mean()
        df['hsgt_ma20'] = df['hsgt_net_amount'].rolling(20).mean()
        
        return df
    
    def analyze_margin_trend(self, days: int = 30) -> pd.DataFrame:
        """
        分析融资融券趋势
        
        Args:
            days: 分析天数
        
        Returns:
            趋势分析DataFrame
        """
        end_date = datetime.datetime.now().strftime('%Y%m%d')
        start_dt = datetime.datetime.now() - datetime.timedelta(days=days)
        start_date = start_dt.strftime('%Y%m%d')
        
        df = self.db.get_margin_history(start_date, end_date)
        if df.empty:
            return pd.DataFrame()
        
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        df = df.sort_values('trade_date')
        
        # 计算变化率
        df['rzye_change'] = df['rzye_market'].pct_change()
        df['rqye_change'] = df['rqye_market'].pct_change()
        
        return df
    
    # 代理方法 - 直接调用数据库方法
    def get_hsgt_by_date(self, trade_date: str) -> Optional[pd.Series]:
        return self.db.get_hsgt_by_date(trade_date)
    
    def get_margin_by_date(self, trade_date: str) -> Optional[pd.Series]:
        return self.db.get_margin_by_date(trade_date)
    
    def get_stock_margin(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        return self.db.get_stock_margin(ts_code, start_date, end_date)
    
    def get_last_update_time(self, action_type: str) -> Optional[str]:
        return self.db.get_last_update_time(action_type)