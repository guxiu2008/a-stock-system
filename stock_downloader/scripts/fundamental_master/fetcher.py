#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务护城河数据工具 - 数据获取模块（优化版：批量股票代码）
"""

import datetime
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import TUSHARE_TOKEN, REQUEST_DELAY

try:
    import tushare as ts
except ImportError:
    print("请先安装 tushare: pip install tushare")
    sys.exit(1)


class FinancialDataFetcher:
    """财务数据获取类 - 从Tushare获取财务数据（批量股票代码模式）"""

    def __init__(self, db_path: str = "stock_data.db"):
        """
        初始化数据获取器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        if TUSHARE_TOKEN:
            ts.set_token(TUSHARE_TOKEN)
            self.pro = ts.pro_api()
        else:
            self.pro = None
            raise RuntimeError("未配置TUSHARE_TOKEN")
        
        self.db_path = db_path

    def fetch_stock_list(self) -> List[str]:
        """
        从资产注册表获取股票列表（避免重复调用API）

        Returns:
            股票代码列表
        """
        print("正在从资产注册表获取股票列表...")
        from sqlalchemy import create_engine, text
        
        engine = create_engine(f"sqlite:///{self.db_path}")
        
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT ts_code FROM dim_stock_info ORDER BY ts_code"))
                stock_list = [row[0] for row in result]
            
            if not stock_list:
                print("警告: 资产注册表中没有股票数据，请先运行 asset_registry 更新")
                # 兜底方案：直接调用 API 获取
                print("尝试直接从 Tushare 获取股票列表...")
                time.sleep(1)
                df = self.pro.stock_basic(
                    exchange='',
                    list_status='L',
                    fields='ts_code'
                )
                if not df.empty:
                    stock_list = df['ts_code'].tolist()
            
            print(f"获取到 {len(stock_list)} 只股票")
            return stock_list
        except Exception as e:
            print(f"从数据库获取股票列表失败: {e}")
            # 兜底方案
            print("尝试直接从 Tushare 获取股票列表...")
            time.sleep(1)
            df = self.pro.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code'
            )
            if df.empty:
                print("未获取到股票列表")
                return []
            return df['ts_code'].tolist()

    def fetch_balancesheet(self, ts_code: str, 
                           start_date: str = None, 
                           end_date: str = None,
                           period: str = None) -> pd.DataFrame:
        """
        获取资产负债表（支持传入多个股票代码，逗号分隔）

        Args:
            ts_code: 股票代码（单个或多个，逗号分隔）
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 报告期 (如 20231231)

        Returns:
            资产负债表DataFrame
        """
        time.sleep(REQUEST_DELAY)

        params = {'ts_code': ts_code}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if period:
            params['period'] = period

        df = self.pro.balancesheet(**params)

        if df.empty:
            return pd.DataFrame()

        # 只保留核心字段
        core_cols = ['ts_code', 'ann_date', 'end_date', 'report_type', 
                     'money_cap', 'accounts_receiv', 'total_assets', 'total_liab', 'update_flag']
        available_cols = [col for col in core_cols if col in df.columns]
        df = df[available_cols].copy()

        df['update_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return df

    def fetch_income(self, ts_code: str, 
                     start_date: str = None, 
                     end_date: str = None,
                     period: str = None) -> pd.DataFrame:
        """
        获取利润表（支持传入多个股票代码，逗号分隔）

        Args:
            ts_code: 股票代码（单个或多个，逗号分隔）
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 报告期 (如 20231231)

        Returns:
            利润表DataFrame
        """
        time.sleep(REQUEST_DELAY)

        params = {'ts_code': ts_code}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if period:
            params['period'] = period

        df = self.pro.income(**params)

        if df.empty:
            return pd.DataFrame()

        # 只保留核心字段
        core_cols = ['ts_code', 'ann_date', 'end_date', 'report_type', 
                     'revenue', 'net_profit', 'kcfjce', 'update_flag']
        available_cols = [col for col in core_cols if col in df.columns]
        df = df[available_cols].copy()

        df['update_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return df

    def fetch_cashflow(self, ts_code: str, 
                       start_date: str = None, 
                       end_date: str = None,
                       period: str = None) -> pd.DataFrame:
        """
        获取现金流量表（支持传入多个股票代码，逗号分隔）

        Args:
            ts_code: 股票代码（单个或多个，逗号分隔）
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 报告期 (如 20231231)

        Returns:
            现金流量表DataFrame
        """
        time.sleep(REQUEST_DELAY)

        params = {'ts_code': ts_code}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if period:
            params['period'] = period

        df = self.pro.cashflow(**params)

        if df.empty:
            return pd.DataFrame()

        # 只保留核心字段
        core_cols = ['ts_code', 'ann_date', 'end_date', 'report_type', 
                     'ncf_from_oa', 'update_flag']
        available_cols = [col for col in core_cols if col in df.columns]
        df = df[available_cols].copy()

        df['update_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return df

    def fetch_fina_indicator(self, ts_code: str, 
                             start_date: str = None, 
                             end_date: str = None,
                             period: str = None) -> pd.DataFrame:
        """
        获取财务指标表（支持传入多个股票代码，逗号分隔）

        Args:
            ts_code: 股票代码（单个或多个，逗号分隔）
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 报告期 (如 20231231)

        Returns:
            财务指标表DataFrame
        """
        time.sleep(REQUEST_DELAY)

        params = {'ts_code': ts_code}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if period:
            params['period'] = period

        df = self.pro.fina_indicator(**params)

        if df.empty:
            return pd.DataFrame()

        # 只保留核心字段
        core_cols = ['ts_code', 'ann_date', 'end_date', 
                     'roe', 'roe_waa', 'roe_dt', 
                     'grossprofit_margin', 'netprofit_margin', 
                     'debt_to_assets']
        available_cols = [col for col in core_cols if col in df.columns]
        df = df[available_cols].copy()

        df['update_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return df

    def _merge_period_data(self, df_balance: pd.DataFrame, df_income: pd.DataFrame,
                           df_cashflow: pd.DataFrame, df_indicator: pd.DataFrame) -> pd.DataFrame:
        """合并同一个报告期的财务数据"""
        merged_df = pd.DataFrame()
        dfs = [df_balance, df_income, df_cashflow, df_indicator]
        dfs = [df for df in dfs if not df.empty]

        if not dfs:
            return pd.DataFrame()

        merged_df = dfs[0].copy()

        for df in dfs[1:]:
            key_cols = ['ts_code', 'end_date']
            common_cols = [col for col in key_cols if col in merged_df.columns and col in df.columns]

            if common_cols:
                new_cols = [col for col in df.columns if col not in merged_df.columns or col in common_cols]
                df_subset = df[new_cols]
                merged_df = pd.merge(merged_df, df_subset, on=common_cols, how='outer')

        if 'ts_code' in merged_df.columns and 'end_date' in merged_df.columns:
            merged_df = merged_df.drop_duplicates(subset=['ts_code', 'end_date'], keep='last')

        return merged_df

    def fetch_all_financial_data(self, ts_code: str, 
                                 start_date: str = None, 
                                 end_date: str = None,
                                 period: str = None) -> pd.DataFrame:
        """
        获取所有财务数据并合并（支持单个或批量股票）

        Args:
            ts_code: 股票代码（单个或多个，逗号分隔）
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            period: 报告期 (如 20231231)

        Returns:
            合并后的财务数据DataFrame
        """
        df_balance = self.fetch_balancesheet(ts_code, start_date, end_date, period)
        df_income = self.fetch_income(ts_code, start_date, end_date, period)
        df_cashflow = self.fetch_cashflow(ts_code, start_date, end_date, period)
        df_indicator = self.fetch_fina_indicator(ts_code, start_date, end_date, period)

        merged_df = self._merge_period_data(df_balance, df_income, df_cashflow, df_indicator)
        return merged_df

    def fetch_by_stock_batch_generator(self, stock_list: List[str], period: str = None, 
                                      batch_size: int = 100):
        """
        批量获取股票财务数据 - 生成器版本（边获取边返回）

        Args:
            stock_list: 股票代码列表
            period: 报告期 (如 20231231)
            batch_size: 每批请求的股票数量，默认 100

        Yields:
            每批的财务数据DataFrame
        """
        import time
        start_time = time.time()
        
        total_batches = (len(stock_list) + batch_size - 1) // batch_size
        print(f"开始批量获取 {len(stock_list)} 只股票的财务数据，分 {total_batches} 批")
        
        total_count = 0
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            ts_codes_str = ','.join(batch)
            print(f"  处理第 {batch_num}/{total_batches} 批: {batch[0]} ... {batch[-1]}")
            
            try:
                df = self.fetch_all_financial_data(ts_codes_str, period=period)
                if not df.empty:
                    total_count += len(df)
                    elapsed = time.time() - start_time
                    print(f"    成功获取 {df['ts_code'].nunique()} 只股票，{len(df)} 条记录，累计 {total_count} 条，耗时 {elapsed:.1f} 秒")
                    yield df
            except Exception as e:
                print(f"    批次失败: {e}")
                continue
        
        elapsed = time.time() - start_time
        print(f"批量获取完成！总耗时: {elapsed:.1f} 秒，总计 {total_count} 条记录")

    def fetch_by_stock_batch(self, stock_list: List[str], period: str = None, 
                            batch_size: int = 100) -> pd.DataFrame:
        """
        批量获取股票财务数据（核心优化方法）

        Args:
            stock_list: 股票代码列表
            period: 报告期 (如 20231231)
            batch_size: 每批请求的股票数量，默认 100

        Returns:
            合并后的财务数据DataFrame
        """
        all_data = []
        for df in self.fetch_by_stock_batch_generator(stock_list, period, batch_size):
            all_data.append(df)
        
        if not all_data:
            return pd.DataFrame()
        
        return pd.concat(all_data, ignore_index=True)

    def fetch_mainbz(self, ts_code: str, period: str = None) -> pd.DataFrame:
        """
        获取主营业务构成（支持逗号分隔批量查询）

        Args:
            ts_code: 股票代码（单个或多个，逗号分隔）
            period: 报告期 (如 20231231)

        Returns:
            主营业务构成DataFrame
        """
        time.sleep(REQUEST_DELAY)

        params = {'ts_code': ts_code}
        if period:
            params['period'] = period

        df = self.pro.fina_mainbz(**params)

        if df.empty:
            return pd.DataFrame()

        core_cols = ['ts_code', 'end_date', 'bz_item', 'bz_type', 'bz_sales', 'bz_profit', 'bz_cost']
        available_cols = [col for col in core_cols if col in df.columns]
        df = df[available_cols].copy()

        df['update_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return df

    def fetch_mainbz_batch_generator(self, stock_list: List[str], period: str = None,
                                     batch_size: int = 100):
        """
        批量获取主营业务构成 - 生成器版本（边获取边返回）

        Args:
            stock_list: 股票代码列表
            period: 报告期 (如 20231231)
            batch_size: 每批请求的股票数量，默认 100

        Yields:
            每批的主营业务构成DataFrame
        """
        start_time = time.time()

        total_batches = (len(stock_list) + batch_size - 1) // batch_size
        print(f"开始批量获取 {len(stock_list)} 只股票的主营业务构成，分 {total_batches} 批")

        total_count = 0
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i + batch_size]
            batch_num = i // batch_size + 1

            ts_codes_str = ','.join(batch)
            print(f"  处理第 {batch_num}/{total_batches} 批: {batch[0]} ... {batch[-1]}")

            try:
                df = self.fetch_mainbz(ts_codes_str, period=period)
                if not df.empty:
                    total_count += len(df)
                    elapsed = time.time() - start_time
                    print(f"    成功获取 {df['ts_code'].nunique()} 只股票，{len(df)} 条记录，累计 {total_count} 条，耗时 {elapsed:.1f} 秒")
                    yield df
            except Exception as e:
                print(f"    批次失败: {e}")
                continue

        elapsed = time.time() - start_time
        print(f"主营业务构成批量获取完成！总耗时: {elapsed:.1f} 秒，总计 {total_count} 条记录")
