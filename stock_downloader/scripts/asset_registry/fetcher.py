#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产注册表 - 数据获取模块
"""

import datetime
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import TUSHARE_TOKEN

try:
    import tushare as ts
except ImportError:
    print("请先安装 tushare: pip install tushare")
    sys.exit(1)


class DataFetcher:
    """数据获取类 - 从Tushare获取资产注册表数据"""
    
    def __init__(self):
        """初始化数据获取器"""
        if TUSHARE_TOKEN:
            ts.set_token(TUSHARE_TOKEN)
            self.pro = ts.pro_api()
        else:
            self.pro = None
            raise RuntimeError("未配置TUSHARE_TOKEN")
    
    def fetch_stock_basic(self) -> pd.DataFrame:
        """
        获取股票基础信息
        
        Returns:
            股票基础信息DataFrame
        """
        print("正在获取股票基础信息...")
        time.sleep(1)  # API调用间隔1秒
        df = self.pro.stock_basic(
            exchange='',
            list_status='L',
            fields='ts_code,symbol,name,area,industry,fullname,enname,market,exchange,curr_type,list_status,list_date,delist_date,is_hs'
        )
        
        if df.empty:
            print("未获取到股票基础信息")
            return pd.DataFrame()
        
        df['update_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return df
    
    def fetch_industry_classify(self) -> pd.DataFrame:
        """
        获取申万行业分类
        
        Returns:
            行业分类DataFrame
        """
        print("正在获取申万行业分类...")
        
        # 获取申万一级行业
        time.sleep(1)  # API调用间隔1秒
        # level: 'L1'=申万一级, 'L2'=申万二级, 'L3'=申万三级
        # src: 'SW2021'=申万2021版行业分类, 'SW'=旧版, 'ZX'=中信, 'THS'=同花顺
        df_sw = self.pro.index_classify(level='L1', src='SW2021')
        
        if df_sw.empty:
            print("未获取到行业分类信息")
            return pd.DataFrame()
        
        all_data = []
        
        # 获取每个行业的成分股
        for _, row in df_sw.iterrows():
            try:
                time.sleep(1)  # 每次API调用间隔1秒
                df_cons = self.pro.index_member(index_code=row['index_code'])
                if not df_cons.empty:
                    # 映射列名并添加行业信息
                    df_cons['industry_type'] = '申万一级'
                    df_cons['industry_code'] = row['index_code']
                    df_cons['industry_name'] = row['industry_name']
                    df_cons['update_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    # 重命名 con_code 为 ts_code
                    df_cons = df_cons.rename(columns={'con_code': 'ts_code'})
                    # 只保留需要的列
                    df_cons = df_cons[['ts_code', 'industry_type', 'industry_code', 'industry_name', 'update_time']]
                    all_data.append(df_cons)
            except Exception as e:
                print(f"获取行业 {row['industry_name']} 成分股失败: {e}")
        
        if all_data:
            df_result = pd.concat(all_data, ignore_index=True)
            # 按 ts_code 和 industry_type 去重，保留最新的一条
            df_result = df_result.drop_duplicates(subset=['ts_code', 'industry_type'], keep='last')
            return df_result
        
        return pd.DataFrame()
    
    def fetch_trade_calendar(self, start_date: str = None, end_date: str = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        获取交易日历
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            (上交所交易日历, 深交所交易日历)
        """
        if not start_date:
            start_date = (datetime.datetime.now() - datetime.timedelta(days=365*5)).strftime('%Y%m%d')
        if not end_date:
            end_date = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime('%Y%m%d')
        
        print(f"正在获取交易日历 ({start_date} ~ {end_date})...")
        
        df_sse = pd.DataFrame()
        df_szse = pd.DataFrame()
        
        # 获取上交所交易日历
        try:
            time.sleep(1)  # API调用间隔1秒
            df_sse = self.pro.trade_cal(exchange='SSE', start_date=start_date, end_date=end_date)
            if not df_sse.empty:
                df_sse['exchange'] = 'SSE'
        except Exception as e:
            print(f"获取上交所交易日历失败: {e}")
        
        # 获取深交所交易日历
        try:
            time.sleep(1)  # API调用间隔1秒
            df_szse = self.pro.trade_cal(exchange='SZSE', start_date=start_date, end_date=end_date)
            if not df_szse.empty:
                df_szse['exchange'] = 'SZSE'
        except Exception as e:
            print(f"获取深交所交易日历失败: {e}")
        
        return df_sse, df_szse
    
    def fetch_concept_classify(self) -> pd.DataFrame:
        """
        获取概念分类（使用concept接口）
        
        Returns:
            概念分类DataFrame
        """
        print("正在获取概念分类...")
        
        # 先获取概念列表
        time.sleep(1)  # API调用间隔1秒
        df_concepts = self.pro.concept()
        
        if df_concepts.empty:
            print("未获取到概念列表")
            return pd.DataFrame()
        
        all_data = []
        
        # 获取每个概念的成分股
        for _, row in df_concepts.iterrows():
            try:
                time.sleep(0.5)  # 每次API调用间隔1秒
                df_cons = self.pro.concept_detail(id=row['code'])
                if not df_cons.empty:
                    df_cons['concept_code'] = row['code']
                    df_cons['concept_name'] = row['name']
                    df_cons['update_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    # 只保留需要的列
                    df_cons = df_cons[['ts_code', 'concept_code', 'concept_name', 'update_time']]
                    all_data.append(df_cons)
            except Exception as e:
                print(f"获取概念 {row['name']} 成分股失败: {e}")
        
        if all_data:
            df_result = pd.concat(all_data, ignore_index=True)
            # 按 ts_code 和 concept_code 去重，保留最新的一条
            df_result = df_result.drop_duplicates(subset=['ts_code', 'concept_code'], keep='last')
            return df_result
        
        return pd.DataFrame()
