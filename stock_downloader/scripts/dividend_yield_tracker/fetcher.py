#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股息率追踪器 - 数据获取模块
"""

import datetime
import sys
import time
from pathlib import Path
from typing import Optional, List

import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import TUSHARE_TOKEN

try:
    import tushare as ts
except ImportError:
    print("请先安装 tushare: pip install tushare")
    sys.exit(1)


class DividendDataFetcher:
    """数据获取类 - 从Tushare获取分红数据"""
    
    def __init__(self):
        """初始化数据获取器"""
        if TUSHARE_TOKEN:
            ts.set_token(TUSHARE_TOKEN)
            self.pro = ts.pro_api()
        else:
            self.pro = None
            raise RuntimeError("未配置TUSHARE_TOKEN")
    
    def fetch_dividend(self, ts_code: Optional[str] = None, 
                       ann_date: Optional[str] = None, 
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取分红送股数据
        
        Args:
            ts_code: 股票代码
            ann_date: 公告日期 (YYYYMMDD)
            end_date: 分红年度 (YYYYMMDD)
        
        Returns:
            分红数据DataFrame
        """
        print(f"正在获取分红数据 (ts_code={ts_code}, ann_date={ann_date}, end_date={end_date})...")
        time.sleep(1)  # API调用间隔1秒
        
        df = self.pro.dividend(
            ts_code=ts_code,
            ann_date=ann_date,
            end_date=end_date,
            fields='ts_code,ann_date,end_date,cash_div_tax,record_date,ex_date,div_proc'
        )
        
        if df.empty:
            print("未获取到分红数据")
            return pd.DataFrame()
        
        df['update_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return df
    
    def fetch_dividend_by_year(self, year: int) -> pd.DataFrame:
        """
        获取指定年度的分红数据
        
        Args:
            year: 年度 (如 2023)
        
        Returns:
            分红数据DataFrame
        """
        end_date = f"{year}1231"
        return self.fetch_dividend(end_date=end_date)
    
    def fetch_dividend_by_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取指定日期范围内的分红数据（通过多次调用API）
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            分红数据DataFrame
        """
        print(f"正在获取 {start_date} 到 {end_date} 的分红数据...")
        
        all_data = []
        
        # 按年份获取数据
        start_year = int(start_date[:4])
        end_year = int(end_date[:4])
        
        for year in range(start_year, end_year + 1):
            df = self.fetch_dividend_by_year(year)
            if not df.empty:
                all_data.append(df)
        
        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            return result
        
        return pd.DataFrame()
    
    def fetch_dividend_history(self, years: int = 10) -> pd.DataFrame:
        """
        获取过去N年的分红历史数据
        
        Args:
            years: 年数
        
        Returns:
            分红数据DataFrame
        """
        current_year = datetime.datetime.now().year
        start_year = current_year - years
        
        start_date = f"{start_year}0101"
        end_date = f"{current_year}1231"
        
        return self.fetch_dividend_by_date_range(start_date, end_date)