#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金流向分析 - 数据获取模块
"""

import datetime
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import TUSHARE_TOKEN

try:
    import tushare as ts
except ImportError:
    print("请先安装 tushare: pip install tushare")
    sys.exit(1)


class MoneyFlowDataFetcher:
    """资金流向数据获取类 - 从Tushare获取北向资金和融资融券数据"""
    
    def __init__(self):
        """初始化数据获取器"""
        if TUSHARE_TOKEN:
            ts.set_token(TUSHARE_TOKEN)
            self.pro = ts.pro_api()
        else:
            self.pro = None
            raise RuntimeError("未配置TUSHARE_TOKEN")
    
    def fetch_hsgt(self, trade_date: str = None, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取北向资金每日流向数据
        
        Args:
            trade_date: 单个交易日 (YYYYMMDD)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            北向资金数据DataFrame
        """
        time.sleep(1)  # API调用间隔1秒
        
        try:
            if trade_date:
                print(f"正在获取 {trade_date} 的北向资金数据...")
                df = self.pro.moneyflow_hsgt(trade_date=trade_date)
            elif start_date and end_date:
                print(f"正在获取 {start_date} ~ {end_date} 的北向资金数据...")
                df = self.pro.moneyflow_hsgt(start_date=start_date, end_date=end_date)
            else:
                # 默认获取最近30天
                end_date = datetime.datetime.now().strftime('%Y%m%d')
                start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')
                print(f"正在获取 {start_date} ~ {end_date} 的北向资金数据...")
                df = self.pro.moneyflow_hsgt(start_date=start_date, end_date=end_date)
            
            if df.empty:
                print("未获取到北向资金数据")
                return pd.DataFrame()
            
            # 字段映射
            df = df.rename(columns={
                'ggt_ss': 'ggt_ss_net_amount',  # 港股通（上海）
                'ggt_sz': 'ggt_sz_net_amount',  # 港股通（深圳）
                'hgt': 'hgt_net_amount',        # 沪股通
                'sgt': 'sgt_net_amount'         # 深股通
            }, errors='ignore')
            
            # 计算北向资金净流入合计（沪股通+深股通）
            df['hsgt_net_amount'] = 0.0
            if 'hgt_net_amount' in df.columns:
                df['hsgt_net_amount'] += pd.to_numeric(df['hgt_net_amount'], errors='coerce').fillna(0)
            if 'sgt_net_amount' in df.columns:
                df['hsgt_net_amount'] += pd.to_numeric(df['sgt_net_amount'], errors='coerce').fillna(0)
            
            # 确保所有数值字段都是数值类型
            numeric_columns = ['ggt_ss_net_amount', 'ggt_sz_net_amount', 'hgt_net_amount', 'sgt_net_amount']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
        except Exception as e:
            print(f"获取北向资金数据失败: {e}")
            return pd.DataFrame()
    
    def fetch_margin(self, trade_date: str = None, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取全市场融资融券余额数据
        
        Args:
            trade_date: 单个交易日 (YYYYMMDD)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            全市场融资融券数据DataFrame
        """
        time.sleep(1)  # API调用间隔1秒
        
        try:
            if trade_date:
                print(f"正在获取 {trade_date} 的全市场融资融券数据...")
                df = self.pro.margin(trade_date=trade_date)
            elif start_date and end_date:
                print(f"正在获取 {start_date} ~ {end_date} 的全市场融资融券数据...")
                df = self.pro.margin(start_date=start_date, end_date=end_date)
            else:
                end_date = datetime.datetime.now().strftime('%Y%m%d')
                start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')
                print(f"正在获取 {start_date} ~ {end_date} 的全市场融资融券数据...")
                df = self.pro.margin(start_date=start_date, end_date=end_date)
            
            if df.empty:
                print("未获取到全市场融资融券数据")
                return pd.DataFrame()
            
            # 字段映射
            df = df.rename(columns={
                'rzye': 'rzye_market',
                'rqye': 'rqye_market'
            }, errors='ignore')
            
            return df
        except Exception as e:
            print(f"获取全市场融资融券数据失败: {e}")
            return pd.DataFrame()
    
    def fetch_margin_detail(self, trade_date: str = None, ts_code: str = None) -> pd.DataFrame:
        """
        获取个股融资融券明细数据
        
        Args:
            trade_date: 交易日 (YYYYMMDD)
            ts_code: 股票代码
        
        Returns:
            个股融资融券明细DataFrame
        """
        time.sleep(1)  # API调用间隔1秒
        
        try:
            if trade_date and ts_code:
                print(f"正在获取 {ts_code} 在 {trade_date} 的融资融券明细...")
                df = self.pro.margin_detail(trade_date=trade_date, ts_code=ts_code)
            elif trade_date:
                print(f"正在获取 {trade_date} 的个股融资融券明细...")
                df = self.pro.margin_detail(trade_date=trade_date)
            elif ts_code:
                print(f"正在获取 {ts_code} 的融资融券明细...")
                df = self.pro.margin_detail(ts_code=ts_code)
            else:
                print("请提供 trade_date 或 ts_code")
                return pd.DataFrame()
            
            if df.empty:
                print("未获取到个股融资融券明细")
                return pd.DataFrame()
            
            return df
        except Exception as e:
            print(f"获取个股融资融券明细失败: {e}")
            return pd.DataFrame()