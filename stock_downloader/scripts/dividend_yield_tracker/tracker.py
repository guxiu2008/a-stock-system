#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股息率追踪器 - 核心业务逻辑模块
"""

import datetime
import sys
from pathlib import Path
from typing import Optional, List, Dict, Tuple

import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .database import DividendYieldTrackerDatabase
from .fetcher import DividendDataFetcher


class DividendYieldTracker:
    """股息率追踪器核心类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        """
        初始化股息率追踪器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db = DividendYieldTrackerDatabase(db_path)
        self.fetcher = DividendDataFetcher()
    
    def sync_dividend_history(self, years: int = 10, force_update: bool = False) -> int:
        """
        同步分红历史数据
        
        Args:
            years: 需要同步的年数
            force_update: 是否强制更新（即使数据库已有数据）
        
        Returns:
            同步的记录数
        """
        current_year = datetime.datetime.now().year
        start_year = current_year - years
        
        total_count = 0
        
        # 按年份逐一下载并保存，避免内存溢出
        for year in range(start_year, current_year + 1):
            end_date = f"{year}1231"
            
            # 检查是否需要更新该年度数据
            if not force_update:
                # 简单检查：如果数据库中已有该年度数据，跳过
                # 实际应用中可以更精细地判断
                existing_df = self.db.get_dividend_by_date_range(end_date, end_date)
                if not existing_df.empty:
                    print(f"跳过 {year} 年数据（已存在）")
                    continue
            
            # 获取该年度分红数据
            df = self.fetcher.fetch_dividend_by_year(year)
            
            if not df.empty:
                # 计算派息率（需要关联财务数据）
                df = self._calculate_payout_ratio(df)
                
                # 保存到数据库
                count = self.db.save_dividend_history(df)
                total_count += count
                print(f"保存 {year} 年分红数据: {count} 条")
                
                # 记录日志
                self.db.log_update(
                    data_type="dividend_history",
                    record_count=count,
                    status="success",
                    start_date=f"{year}0101",
                    end_date=end_date
                )
            else:
                print(f"{year} 年无分红数据")
        
        return total_count
    
    def sync_latest_dividends(self) -> int:
        """
        同步最新的分红数据（用于日常监控）
        
        Returns:
            同步的记录数
        """
        current_year = datetime.datetime.now().year
        
        # 获取当前年度的分红数据
        df = self.fetcher.fetch_dividend_by_year(current_year)
        
        if df.empty:
            print("暂无最新分红数据")
            return 0
        
        # 计算派息率
        df = self._calculate_payout_ratio(df)
        
        # 保存到数据库
        count = self.db.save_dividend_history(df)
        print(f"保存最新分红数据: {count} 条")
        
        # 记录日志
        self.db.log_update(
            data_type="latest_dividends",
            record_count=count,
            status="success",
            start_date=f"{current_year}0101",
            end_date=f"{current_year}1231"
        )
        
        return count
    
    def _calculate_payout_ratio(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算派息率
        
        Args:
            df: 分红数据DataFrame
        
        Returns:
            增加了payout_ratio列的DataFrame
        """
        payout_ratios = []
        
        for _, row in df.iterrows():
            ts_code = row['ts_code']
            end_date = row['end_date']
            cash_div_tax = row.get('cash_div_tax', 0)
            
            payout_ratio = None
            
            # 获取净利润
            net_profit = self.db.get_net_profit(ts_code, end_date)
            
            if net_profit and net_profit > 0 and cash_div_tax and cash_div_tax > 0:
                # 尝试从财务报表中获取更多信息来计算总股本
                # 方法：获取财务数据，使用ROE和净资产来估算
                financial_df = self.db.fact_financial_reports.get(ts_code=ts_code, end_date=end_date)
                
                if not financial_df.empty:
                    financial_row = financial_df.iloc[0]
                    roe = financial_row.get('roe')
                    net_profit_from_report = financial_row.get('net_profit')
                    
                    # 使用财务报表中的净利润（更准确）
                    if pd.notna(net_profit_from_report) and net_profit_from_report > 0:
                        net_profit = net_profit_from_report
                    
                    # 如果有ROE和净资产，我们可以估算总股本
                    # 但为了简化，我们使用一个更直接的方法：
                    # 派息率 = 分红总额 / 净利润
                    # 由于我们只有每股派息，我们假设总股本为1（保守估计）
                    # 实际应用中需要从其他接口获取总股本数据
                    
                    # 这里我们使用一个简化的估算方法：
                    # 假设每股净资产 = 1元（简化计算）
                    # 派息率 = 每股派息 / (每股收益)
                    # 但由于没有每股收益，我们使用ROE来估算
                    
                    if pd.notna(roe) and roe > 0:
                        # 估算每股收益 = 每股净资产 × ROE
                        # 假设每股净资产为1元
                        eps_estimate = roe / 100  # ROE是百分比
                        if eps_estimate > 0:
                            payout_ratio = cash_div_tax / eps_estimate
                    else:
                        # 备用方案：直接使用现金分红与净利润的比例
                        # 由于没有总股本，我们记录一个估算值，或者使用None
                        # 这里我们使用None，并在日志中说明
                        payout_ratio = None
                else:
                    # 没有财务数据时，无法计算
                    payout_ratio = None
            
            payout_ratios.append(payout_ratio)
        
        df['payout_ratio'] = payout_ratios
        return df
    
    def calculate_static_yield(self, ts_code: str) -> Optional[float]:
        """
        计算静态股息率
        
        静态股息率 = 当年派息 / 当前股价
        
        Args:
            ts_code: 股票代码
        
        Returns:
            静态股息率（小数形式，如0.05表示5%），如果无法计算返回None
        """
        # 获取最新分红数据
        df = self.db.get_dividend_by_ts_code(ts_code)
        if df.empty:
            return None
        
        # 获取最新一年的派息（只考虑已实施的）
        latest_div = df[df['div_proc'] == '实施'].iloc[0] if not df[df['div_proc'] == '实施'].empty else df.iloc[0]
        cash_div_tax = latest_div.get('cash_div_tax', 0)
        
        if not cash_div_tax or cash_div_tax <= 0:
            return None
        
        # 获取最新收盘价
        close_price = self.db.get_latest_close_price(ts_code)
        if not close_price or close_price <= 0:
            return None
        
        return cash_div_tax / close_price
    
    def check_dividend_sustainability(self, ts_code: str, years: int = 5) -> Dict:
        """
        检查分红可持续性
        
        Args:
            ts_code: 股票代码
            years: 需要检查的年数
        
        Returns:
            包含可持续性分析结果的字典
        """
        df = self.db.get_dividend_by_ts_code(ts_code)
        
        if df.empty:
            return {
                "ts_code": ts_code,
                "is_sustainable": False,
                "reason": "无分红数据",
                "dividend_years": 0,
                "continuous_years": 0,
                "is_growing": False
            }
        
        # 只考虑已实施的分红
        df_implemented = df[df['div_proc'] == '实施'].copy()
        if df_implemented.empty:
            df_implemented = df
        
        # 按年度去重，保留每年最新的一条
        df_implemented['year'] = df_implemented['end_date'].str[:4]
        df_yearly = df_implemented.drop_duplicates(subset=['year'], keep='first')
        df_yearly = df_yearly.sort_values('year', ascending=False)
        
        dividend_years = len(df_yearly)
        continuous_years = 0
        is_growing = False
        
        # 检查连续分红年数
        current_year = int(datetime.datetime.now().year)
        expected_year = current_year
        
        for _, row in df_yearly.iterrows():
            year = int(row['year'])
            if year == expected_year:
                continuous_years += 1
                expected_year -= 1
            else:
                break
        
        # 检查分红金额是否增长
        if len(df_yearly) >= 2:
            recent_dividends = df_yearly.head(years)['cash_div_tax'].dropna()
            if len(recent_dividends) >= 2:
                is_growing = recent_dividends.iloc[0] >= recent_dividends.iloc[-1]
        
        is_sustainable = continuous_years >= 3
        
        reason = ""
        if not is_sustainable:
            reason = f"连续分红年数不足（仅{continuous_years}年）"
        elif not is_growing and dividend_years >= 3:
            reason = "分红金额未增长"
        else:
            reason = "分红稳定可持续"
        
        return {
            "ts_code": ts_code,
            "is_sustainable": is_sustainable,
            "reason": reason,
            "dividend_years": dividend_years,
            "continuous_years": continuous_years,
            "is_growing": is_growing
        }
    
    def get_cash_cow_list(self, min_yield: float = 0.05, max_payout_ratio: float = 1.0) -> pd.DataFrame:
        """
        获取高股息股票列表（现金牛）
        
        Args:
            min_yield: 最低股息率（默认5%）
            max_payout_ratio: 最高派息率（默认100%）
        
        Returns:
            高股息股票DataFrame
        """
        # 获取所有分红数据
        all_dividends = self.db.get_all_dividends()
        
        if all_dividends.empty:
            return pd.DataFrame()
        
        # 获取每只股票最新的分红
        all_dividends['year'] = all_dividends['end_date'].str[:4]
        latest_dividends = all_dividends.sort_values(['ts_code', 'year'], ascending=[True, False])
        latest_dividends = latest_dividends.drop_duplicates(subset=['ts_code'], keep='first')
        
        cash_cows = []
        
        for _, row in latest_dividends.iterrows():
            ts_code = row['ts_code']
            
            # 计算静态股息率
            static_yield = self.calculate_static_yield(ts_code)
            
            if static_yield and static_yield >= min_yield:
                # 检查派息率
                payout_ratio = row.get('payout_ratio')
                if payout_ratio and payout_ratio > max_payout_ratio:
                    continue
                
                # 检查分红可持续性
                sustainability = self.check_dividend_sustainability(ts_code)
                
                cash_cows.append({
                    "ts_code": ts_code,
                    "static_yield": static_yield,
                    "cash_div_tax": row.get('cash_div_tax'),
                    "end_date": row.get('end_date'),
                    "ex_date": row.get('ex_date'),
                    "div_proc": row.get('div_proc'),
                    "payout_ratio": payout_ratio,
                    "is_sustainable": sustainability['is_sustainable'],
                    "continuous_years": sustainability['continuous_years']
                })
        
        result_df = pd.DataFrame(cash_cows)
        if not result_df.empty:
            result_df = result_df.sort_values('static_yield', ascending=False)
        
        return result_df
    
    def get_upcoming_dividends(self) -> pd.DataFrame:
        """
        获取即将分红的股票列表（已公告但未到登记日）
        
        Returns:
            即将分红的股票DataFrame
        """
        current_date = datetime.datetime.now().strftime('%Y%m%d')
        
        # 获取所有分红数据
        all_dividends = self.db.get_all_dividends()
        
        if all_dividends.empty:
            return pd.DataFrame()
        
        # 筛选：已公告、有登记日、登记日大于当前日期
        upcoming = all_dividends[
            (all_dividends['record_date'].notna()) &
            (all_dividends['record_date'] > current_date)
        ].copy()
        
        if not upcoming.empty:
            upcoming = upcoming.sort_values('record_date')
        
        return upcoming