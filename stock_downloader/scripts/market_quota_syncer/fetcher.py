#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股行情同步工具 - 数据获取模块
"""

import datetime
import sys
import time
from pathlib import Path
from typing import Optional, List, Tuple

import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import TUSHARE_TOKEN

try:
    import tushare as ts
except ImportError:
    print("请先安装 tushare: pip install tushare")
    sys.exit(1)


class MarketQuotaFetcher:
    """行情数据获取类 - 从Tushare获取行情数据"""
    
    # 主流指数列表
    INDEX_LIST = [
        '000001.SH',  # 上证指数
        '399001.SZ',  # 深证成指
        '000300.SH',  # 沪深300
        '399006.SZ',  # 创业板指
        '000852.SH'   # 中证1000
    ]
    
    def __init__(self):
        """初始化数据获取器"""
        if TUSHARE_TOKEN:
            ts.set_token(TUSHARE_TOKEN)
            self.pro = ts.pro_api()
        else:
            self.pro = None
            raise RuntimeError("未配置TUSHARE_TOKEN")
    
    def fetch_stock_list(self) -> List[str]:
        """
        获取股票列表
        
        Returns:
            股票代码列表
        """
        print("正在获取股票列表...")
        time.sleep(0.3)
        df = self.pro.stock_basic(exchange='', list_status='L', fields='ts_code')
        
        if df.empty:
            print("未获取到股票列表")
            return []
        
        return df['ts_code'].tolist()
    
    def fetch_daily_quotes(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取个股日线行情数据
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            行情数据DataFrame
        """
        time.sleep(0.3)
        df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        
        if df.empty:
            return pd.DataFrame()
        
        return df
    
    def fetch_adj_factor(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取复权因子
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            复权因子DataFrame
        """
        time.sleep(0.3)
        df = self.pro.adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
        
        if df.empty:
            return pd.DataFrame()
        
        return df
    
    def fetch_stock_quotes_with_adj(self, ts_code: str, start_date: str = None, 
                                      end_date: str = None) -> pd.DataFrame:
        """
        获取个股行情并计算前复权价格
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            带前复权价格的行情DataFrame
        """
        # 获取日线行情
        df_daily = self.fetch_daily_quotes(ts_code, start_date, end_date)
        if df_daily.empty:
            return pd.DataFrame()
        
        # 获取复权因子
        df_adj = self.fetch_adj_factor(ts_code, start_date, end_date)
        
        # 合并数据
        if not df_adj.empty:
            df = pd.merge(df_daily, df_adj, on=['ts_code', 'trade_date'], how='left')
        else:
            df = df_daily
            df['adj_factor'] = 1.0
        
        # 按日期降序排列（最新日期在前）
        df = df.sort_values('trade_date', ascending=False).reset_index(drop=True)
        
        # 计算前复权价格
        # 前复权 = 原始价格 × 当日复权因子 / 最新复权因子
        if len(df) > 0:
            latest_adj_factor = df.loc[0, 'adj_factor']
            # 处理除零情况：如果最新复权因子为0，则设为1.0
            if latest_adj_factor == 0 or pd.isna(latest_adj_factor):
                latest_adj_factor = 1.0
            df['adj_open'] = df['open'] * df['adj_factor'] / latest_adj_factor
            df['adj_high'] = df['high'] * df['adj_factor'] / latest_adj_factor
            df['adj_low'] = df['low'] * df['adj_factor'] / latest_adj_factor
            df['adj_close'] = df['close'] * df['adj_factor'] / latest_adj_factor
        
        # 按日期升序排列
        df = df.sort_values('trade_date', ascending=True).reset_index(drop=True)
        
        return df
    
    def fetch_index_daily(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取指数日线行情
        
        Args:
            ts_code: 指数代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            指数行情DataFrame
        """
        time.sleep(0.3)
        df = self.pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        
        if df.empty:
            return pd.DataFrame()
        
        return df
    
    def fetch_all_index_quotes(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取所有主流指数的行情
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            所有指数行情DataFrame
        """
        all_data = []
        
        for index_code in self.INDEX_LIST:
            try:
                print(f"正在获取指数 {index_code} 行情...")
                df = self.fetch_index_daily(index_code, start_date, end_date)
                if not df.empty:
                    all_data.append(df)
            except Exception as e:
                print(f"获取指数 {index_code} 行情失败: {e}")
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        
        return pd.DataFrame()

    # ==================== 批量获取（优化模式）====================

    def fetch_daily_quotes_batch(self, ts_codes: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        批量获取个股日线行情数据（一次多只股票）
        
        Args:
            ts_codes: 股票代码，逗号分隔
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            行情数据DataFrame
        """
        time.sleep(0.3)
        df = self.pro.daily(ts_code=ts_codes, start_date=start_date, end_date=end_date)
        
        if df.empty:
            return pd.DataFrame()
        
        return df

    def fetch_adj_factor_batch(self, ts_codes: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        批量获取复权因子（一次多只股票）
        
        Args:
            ts_codes: 股票代码，逗号分隔
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            复权因子DataFrame
        """
        time.sleep(0.3)
        df = self.pro.adj_factor(ts_code=ts_codes, start_date=start_date, end_date=end_date)
        
        if df.empty:
            return pd.DataFrame()
        
        return df

    def fetch_by_stock_batch_generator(self, stock_list: List[str], start_date: str = None, 
                                       end_date: str = None, batch_size: int = 100):
        """
        批量获取多只股票的行情数据 - 生成器版本（边获取边返回）
        
        Args:
            stock_list: 股票代码列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            batch_size: 每批请求的股票数量
        
        Yields:
            每批的行情DataFrame
        """
        import time
        print(f"开始批量获取 {len(stock_list)} 只股票的行情数据，分 {(len(stock_list) + batch_size - 1) // batch_size} 批")
        
        start_time = time.time()
        total_count = 0
        
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i + batch_size]
            ts_codes_str = ",".join(batch)
            
            print(f"  处理第 {i//batch_size + 1}/{(len(stock_list) + batch_size - 1) // batch_size} 批: {batch[0]} ... {batch[-1]}")
            
            try:
                # 批量获取日线行情
                df_daily = self.fetch_daily_quotes_batch(ts_codes_str, start_date, end_date)
                if df_daily.empty:
                    print(f"    本批无日线数据")
                    continue
                
                # 批量获取复权因子
                df_adj = self.fetch_adj_factor_batch(ts_codes_str, start_date, end_date)
                
                # 合并数据
                if not df_adj.empty:
                    df = pd.merge(df_daily, df_adj, on=['ts_code', 'trade_date'], how='left')
                else:
                    df = df_daily
                    df['adj_factor'] = 1.0
                
                # 按股票分组计算前复权价格
                df_list = []
                for ts_code in batch:
                    df_stock = df[df['ts_code'] == ts_code].copy()
                    if df_stock.empty:
                        continue
                    
                    # 按日期降序排列
                    df_stock = df_stock.sort_values('trade_date', ascending=False).reset_index(drop=True)
                    
                    # 计算前复权
                    latest_adj_factor = df_stock.loc[0, 'adj_factor'] if len(df_stock) > 0 else 1.0
                    if pd.isna(latest_adj_factor) or latest_adj_factor == 0:
                        latest_adj_factor = 1.0
                    
                    df_stock['adj_open'] = df_stock['open'] * df_stock['adj_factor'] / latest_adj_factor
                    df_stock['adj_high'] = df_stock['high'] * df_stock['adj_factor'] / latest_adj_factor
                    df_stock['adj_low'] = df_stock['low'] * df_stock['adj_factor'] / latest_adj_factor
                    df_stock['adj_close'] = df_stock['close'] * df_stock['adj_factor'] / latest_adj_factor
                    
                    # 恢复按日期升序
                    df_stock = df_stock.sort_values('trade_date', ascending=True).reset_index(drop=True)
                    df_list.append(df_stock)
                
                if df_list:
                    batch_df = pd.concat(df_list, ignore_index=True)
                    total_count += len(batch_df)
                    elapsed = time.time() - start_time
                    print(f"    成功获取 {batch_df['ts_code'].nunique()} 只股票，{len(batch_df)} 条记录，累计 {total_count} 条，耗时 {elapsed:.1f} 秒")
                    yield batch_df
                
            except Exception as e:
                print(f"    本批获取失败: {e}")
                continue
        
        elapsed = time.time() - start_time
        print(f"批量获取完成！总耗时: {elapsed:.1f} 秒，总计 {total_count} 条记录")

    def fetch_by_stock_batch(self, stock_list: List[str], start_date: str = None, 
                             end_date: str = None, batch_size: int = 100) -> pd.DataFrame:
        """
        批量获取多只股票的行情数据（含前复权）
        
        Args:
            stock_list: 股票代码列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            batch_size: 每批请求的股票数量
        
        Returns:
            所有股票的行情DataFrame
        """
        all_data = []
        for df in self.fetch_by_stock_batch_generator(stock_list, start_date, end_date, batch_size):
            all_data.append(df)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        
        print("批量获取无数据")
        return pd.DataFrame()
