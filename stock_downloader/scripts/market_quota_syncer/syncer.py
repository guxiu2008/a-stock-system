#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股行情同步工具 - 同步器核心模块（优化版：批量获取模式）
参考 main.py 实现方式：只做增量同步，同步时计算技术指标
"""

import datetime
import time
from typing import Optional, List, Tuple

import pandas as pd

from .database import MarketDatabase as MarketQuotaDB
from .fetcher import MarketQuotaFetcher
from .indicators import MarketTechnicalIndicators


class MarketQuotaSyncer:
    """行情同步器主类"""
    
    def __init__(self, db_path: str = "stock_data.db"):
        """
        初始化行情同步器
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db = MarketQuotaDB(db_path)
        self.fetcher = None
    
    def _ensure_fetcher(self):
        """确保数据获取器已初始化"""
        if self.fetcher is None:
            self.fetcher = MarketQuotaFetcher()
    
    def sync_single_stock(self, ts_code: str, request_delay: float = 0.3) -> int:
        """
        同步单只股票行情（仅增量同步），并计算技术指标
        
        Args:
            ts_code: 股票代码
            request_delay: 请求间隔时间（秒）
        
        Returns:
            同步的记录数
        """
        self._ensure_fetcher()
        
        # 获取最后同步日期，确定增量同步范围
        last_date = self.db.get_last_trade_date(ts_code, is_index=False)
        
        if last_date:
            start_date = self._next_day(last_date)
            print(f"增量更新 {ts_code} 从 {start_date} 开始")
        else:
            start_date = '20000101'
            print(f"首次下载 {ts_code}")
        
        end_date = datetime.datetime.now().strftime('%Y%m%d')
        
        try:
            df = self.fetcher.fetch_stock_quotes_with_adj(ts_code, start_date, end_date)
            
            if df.empty:
                print(f"{ts_code} 没有新数据")
                self.db.update_stock_sync_status(ts_code, last_date or '', 'no_data')
                self.db.log_sync('stock', ts_code, start_date, end_date, 0, 'no_data')
                return 0
            
            print(f"下载 {ts_code} 成功，共 {len(df)} 条数据")
            
            count = self.db.save_daily_quotes(df)
            
            # 获取全部历史数据用于计算技术指标
            full_df = self.db.get_history_prices(ts_code)
            
            if len(full_df) > 0:
                # 计算所有技术指标
                indicators_df = MarketTechnicalIndicators.calculate_all(full_df)
                
                # 删除旧的技术指标，保存新的
                self.db.delete_indicators_by_ts_code(ts_code)
                self.db.save_indicators(indicators_df)
                print(f"计算并保存 {ts_code} 技术指标成功")
            
            # 更新同步状态
            latest_date = df['trade_date'].max()
            self.db.update_stock_sync_status(ts_code, latest_date, 'success')
            self.db.log_sync('stock', ts_code, start_date, end_date, count, 'success')
            
            return count
            
        except Exception as e:
            print(f"下载 {ts_code} 失败: {str(e)}")
            last_date = self.db.get_last_trade_date(ts_code, is_index=False)
            self.db.update_stock_sync_status(ts_code, last_date or '', 'failed')
            self.db.log_sync('stock', ts_code, start_date, end_date, 0, 'failed')
            time.sleep(1)
            return 0
    
    def sync_all_stocks(self, max_stocks: int = None, request_delay: float = 0.3, 
                       stock_list: List[str] = None) -> int:
        """
        同步所有股票行情（仅增量同步）- 保留旧方法用于向后兼容
        
        Args:
            max_stocks: 最多同步股票数量（用于测试）
            request_delay: 请求间隔时间（秒）
            stock_list: 指定股票列表，None则获取全部
        
        Returns:
            总同步记录数
        """
        self._ensure_fetcher()
        
        if stock_list is None:
            stock_list = self.fetcher.fetch_stock_list()
        
        if not stock_list:
            print("没有股票可同步")
            return 0
        
        if max_stocks:
            stock_list = stock_list[:max_stocks]
        
        print("=" * 60)
        print(f"开始同步 {len(stock_list)} 只股票行情（单只模式）")
        print("=" * 60)
        
        total_count = 0
        success_count = 0
        
        for i, ts_code in enumerate(stock_list, 1):
            print(f"[{i}/{len(stock_list)}] ", end="")
            count = self.sync_single_stock(ts_code)
            total_count += count
            if count > 0:
                success_count += 1
            
            if i < len(stock_list):
                time.sleep(request_delay)
        
        print("=" * 60)
        print(f"股票同步完成，共 {success_count}/{len(stock_list)} 只成功，{total_count} 条记录")
        print("=" * 60)
        
        self.db.log_sync('all_stocks', None, None, None, total_count, 'success')
        
        return total_count
    
    # ==================== 批量同步（优化模式）====================
    
    def sync_all_stocks_batch(self, max_stocks: int = None, request_delay: float = 0.3,
                              stock_list: List[str] = None, batch_size: int = 100,
                              calculate_indicators: bool = True) -> int:
        """
        批量同步所有股票行情（仅增量同步）- 优化模式（边下载边入库）
        
        Args:
            max_stocks: 最多同步股票数量（用于测试）
            request_delay: 请求间隔时间（秒）
            stock_list: 指定股票列表，None则获取全部
            batch_size: 每批请求的股票数量
            calculate_indicators: 是否计算技术指标（默认 False，因为很慢）
        
        Returns:
            总同步记录数
        """
        import time
        self._ensure_fetcher()
        
        if stock_list is None:
            stock_list = self.fetcher.fetch_stock_list()
        
        if not stock_list:
            print("没有股票可同步")
            return 0
        
        if max_stocks:
            stock_list = stock_list[:max_stocks]
        
        # 获取所有股票的最后同步日期，确定统一的增量同步范围
        print("正在获取股票同步状态...")
        sync_status = self.db.get_all_sync_status(is_index=False)
        last_dates = {}
        if not sync_status.empty:
            for _, row in sync_status.iterrows():
                last_dates[row['ts_code']] = row.get('last_trade_date', '')
        
        # 确定全局的起始日期（取最早的未同步日期）
        global_start_date = None
        for ts_code in stock_list:
            ld = last_dates.get(ts_code, '')
            if ld:
                sd = self._next_day(ld)
            else:
                sd = '20000101'
            if global_start_date is None or sd < global_start_date:
                global_start_date = sd
        
        # 如果没有指定起始日期，默认取最近 30 天（避免首次全量下载太慢）
        if global_start_date is None or global_start_date < '20200101':
            thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
            global_start_date = thirty_days_ago.strftime('%Y%m%d')
            print(f"未找到同步状态，默认从 {global_start_date} 开始更新（最近 30 天）")
        
        end_date = datetime.datetime.now().strftime('%Y%m%d')
        
        print("=" * 60)
        print(f"开始批量同步 {len(stock_list)} 只股票行情")
        print(f"日期范围: {global_start_date} ~ {end_date}, 批次大小: {batch_size}")
        print(f"技术指标计算: {'开启' if calculate_indicators else '关闭'}")
        print("=" * 60)
        
        total_start_time = time.time()
        total_count = 0
        all_updated_stocks = []
        
        # 分批处理：获取一批，入库一批，避免内存占用过大
        # 使用生成器模式，边获取边保存
        for df_batch in self.fetcher.fetch_by_stock_batch_generator(stock_list, global_start_date, end_date, batch_size):
            if df_batch.empty:
                print(f"  本批次没有新数据")
                time.sleep(request_delay)
                continue
            
            # 立即保存到数据库
            print(f"  正在保存 {len(df_batch)} 条记录...")
            count_batch = self.db.save_daily_quotes(df_batch)
            total_count += count_batch
            
            # 更新同步状态并立即计算技术指标
            print(f"  正在更新同步状态...")
            updated_stocks_batch = df_batch['ts_code'].unique()
            all_updated_stocks.extend(updated_stocks_batch)
            
            for ts_code in updated_stocks_batch:
                df_stock = df_batch[df_batch['ts_code'] == ts_code]
                latest_date = df_stock['trade_date'].max()
                self.db.update_stock_sync_status(ts_code, latest_date, 'success')
                
                # 每只股票保存完立即计算技术指标
                if calculate_indicators:
                    try:
                        full_df = self.db.get_history_prices(ts_code)
                        if len(full_df) > 0:
                            indicators_df = MarketTechnicalIndicators.calculate_all(full_df)
                            self.db.delete_indicators_by_ts_code(ts_code)
                            self.db.save_indicators(indicators_df)
                    except Exception as e:
                        print(f"    计算 {ts_code} 指标失败: {e}")
                        continue
            
            print(f"  批次完成，已保存 {count_batch} 条记录")
            
            # 批次间延迟
            time.sleep(request_delay)
        
        total_elapsed = time.time() - total_start_time
        self.db.log_sync('all_stocks', None, global_start_date, end_date, total_count, 'success')
        
        print("\n" + "=" * 60)
        print(f"批量同步完成！")
        print(f"更新股票数: {len(set(all_updated_stocks))}, 总记录数: {total_count}")
        print(f"总耗时: {total_elapsed:.2f} 秒")
        print("=" * 60)
        
        return total_count
    
    def sync_single_index(self, ts_code: str, calculate_indicators: bool = True) -> int:
        """
        同步单只指数行情（仅增量同步），并计算技术指标
        
        Args:
            ts_code: 指数代码
            calculate_indicators: 是否计算并写入技术指标到 market_indicators
        
        Returns:
            同步的记录数
        """
        self._ensure_fetcher()
        
        last_date = self.db.get_last_trade_date(ts_code, is_index=True)
        
        if last_date:
            start_date = self._next_day(last_date)
            print(f"增量更新 {ts_code} 从 {start_date} 开始")
        else:
            start_date = '20000101'
            print(f"首次下载 {ts_code}")
        
        end_date = datetime.datetime.now().strftime('%Y%m%d')
        
        try:
            df = self.fetcher.fetch_index_daily(ts_code, start_date, end_date)
            
            if df.empty:
                print(f"{ts_code} 没有新数据")
                self.db.update_index_sync_status(ts_code, last_date or '', 'no_data')
                self.db.log_sync('index', ts_code, start_date, end_date, 0, 'no_data')
                return 0
            
            print(f"下载 {ts_code} 成功，共 {len(df)} 条数据")
            
            count = self.db.save_index_daily(df)
            
            # 计算并写入指数技术指标（与个股逻辑对称）
            if calculate_indicators:
                try:
                    full_df = self.db.get_history_prices(ts_code, is_index=True)
                    if len(full_df) > 0:
                        indicators_df = MarketTechnicalIndicators.calculate_all(full_df)
                        self.db.delete_indicators_by_ts_code(ts_code)
                        self.db.save_indicators(indicators_df)
                        print(f"计算并保存 {ts_code} 技术指标成功")
                except Exception as e:
                    print(f"计算 {ts_code} 指标失败: {e}")
            
            latest_date = df['trade_date'].max()
            self.db.update_index_sync_status(ts_code, latest_date, 'success')
            self.db.log_sync('index', ts_code, start_date, end_date, count, 'success')
            
            return count
            
        except Exception as e:
            print(f"下载 {ts_code} 失败: {str(e)}")
            last_date = self.db.get_last_trade_date(ts_code, is_index=True)
            self.db.update_index_sync_status(ts_code, last_date or '', 'failed')
            self.db.log_sync('index', ts_code, start_date, end_date, 0, 'failed')
            return 0
    
    def sync_all_indices(self, request_delay: float = 0.3,
                         calculate_indicators: bool = True) -> int:
        """
        同步所有指数行情（仅增量同步），并计算技术指标
        
        Args:
            request_delay: 请求间隔时间（秒）
            calculate_indicators: 是否计算并写入技术指标到 market_indicators
        
        Returns:
            总同步记录数
        """
        self._ensure_fetcher()
        
        print("=" * 60)
        print("开始同步指数行情")
        print(f"技术指标计算: {'开启' if calculate_indicators else '关闭'}")
        print("=" * 60)
        
        total_count = 0
        
        for i, index_code in enumerate(MarketQuotaFetcher.INDEX_LIST, 1):
            count = self.sync_single_index(index_code, calculate_indicators=calculate_indicators)
            total_count += count
            
            if i < len(MarketQuotaFetcher.INDEX_LIST):
                time.sleep(request_delay)
        
        print("=" * 60)
        print(f"指数同步完成，共 {total_count} 条记录")
        print("=" * 60)
        
        self.db.log_sync('all_indices', None, None, None, total_count, 'success')
        
        return total_count
    
    def sync_all(self, max_stocks: int = None, request_delay: float = 0.3, 
                stock_list: List[str] = None, use_batch: bool = True,
                batch_size: int = 100, calculate_indicators: bool = True):
        """
        同步所有数据（股票+指数，仅增量同步）
        
        Args:
            max_stocks: 最多同步股票数量（用于测试）
            request_delay: 请求间隔时间（秒）
            stock_list: 指定股票列表
            use_batch: 是否使用批量模式（默认 True）
            batch_size: 批量模式下每批的股票数
            calculate_indicators: 是否计算技术指标（默认 False）
        """
        print("=" * 60)
        print("开始同步所有行情数据")
        print("=" * 60)
        
        try:
            self.sync_all_indices(request_delay, calculate_indicators=calculate_indicators)
        except Exception as e:
            print(f"同步指数失败: {e}")
        
        try:
            if use_batch:
                self.sync_all_stocks_batch(max_stocks, request_delay, stock_list, batch_size, calculate_indicators)
            else:
                self.sync_all_stocks(max_stocks, request_delay, stock_list)
        except Exception as e:
            print(f"同步股票失败: {e}")
        
        print("=" * 60)
        print("所有行情数据同步完成")
        print("=" * 60)
    
    # 代理方法
    def get_history_prices(self, ts_code: str, start_date: str = None, end_date: str = None, 
                          is_index: bool = False) -> pd.DataFrame:
        return self.db.get_history_prices(ts_code, start_date, end_date, is_index)
    
    def get_indicators(self, ts_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        return self.db.get_indicators(ts_code, start_date, end_date)
    
    def calculate_drawdown(self, ts_code: str, window: int = 252, is_index: bool = False) -> Tuple[float, pd.DataFrame]:
        return self.db.calculate_drawdown(ts_code, window, is_index)
    
    def detect_volume_surge(self, ts_code: str, short_window: int = 5, long_window: int = 20) -> Tuple[bool, float]:
        return self.db.detect_volume_surge(ts_code, short_window, long_window)
    
    def get_all_sync_status(self, is_index: bool = False) -> pd.DataFrame:
        return self.db.get_all_sync_status(is_index)
    
    def calculate_indicators_all(self, max_stocks: int = None, stock_list: List[str] = None,
                                 include_indices: bool = True) -> int:
        """
        单独计算所有股票（以及可选的指数）的技术指标（不获取新数据）
        
        Args:
            max_stocks: 最多计算股票数量（不影响指数）
            stock_list: 指定股票列表
            include_indices: 是否同时回填 MarketQuotaFetcher.INDEX_LIST 中所有指数的技术指标
        
        Returns:
            处理的总数量（股票 + 指数）
        """
        import time
        print("=" * 60)
        print("开始计算所有股票的技术指标")
        print("=" * 60)
        
        # 获取股票列表
        if stock_list is None:
            sync_status = self.db.get_all_sync_status(is_index=False)
            if sync_status.empty:
                print("没有股票数据")
                stock_list = []
            else:
                stock_list = sync_status['ts_code'].tolist()
        
        if max_stocks:
            stock_list = stock_list[:max_stocks]
        
        print(f"共 {len(stock_list)} 只股票需要计算\n")
        
        total_start = time.time()
        success_count = 0
        
        for i, ts_code in enumerate(stock_list, 1):
            if i % 100 == 0 or i == 1 or i == len(stock_list):
                print(f"[{i}/{len(stock_list)}] 处理 {ts_code} ...")
            
            try:
                full_df = self.db.get_history_prices(ts_code)
                if len(full_df) > 0:
                    indicators_df = MarketTechnicalIndicators.calculate_all(full_df)
                    self.db.delete_indicators_by_ts_code(ts_code)
                    self.db.save_indicators(indicators_df)
                    success_count += 1
            except Exception as e:
                print(f"    {ts_code} 计算失败: {e}")
                continue
        
        # 回填所有指数的技术指标
        if include_indices:
            print("\n" + "=" * 60)
            print("开始回填所有指数的技术指标")
            print("=" * 60)
            index_list = MarketQuotaFetcher.INDEX_LIST
            for i, ts_code in enumerate(index_list, 1):
                print(f"[{i}/{len(index_list)}] 处理指数 {ts_code} ...")
                try:
                    full_df = self.db.get_history_prices(ts_code, is_index=True)
                    if len(full_df) > 0:
                        indicators_df = MarketTechnicalIndicators.calculate_all(full_df)
                        self.db.delete_indicators_by_ts_code(ts_code)
                        self.db.save_indicators(indicators_df)
                        success_count += 1
                        print(f"    {ts_code} 完成，共 {len(indicators_df)} 条")
                    else:
                        print(f"    {ts_code} 在 fact_index_daily 中无数据，跳过")
                except Exception as e:
                    print(f"    {ts_code} 计算失败: {e}")
                    continue
        
        total_elapsed = time.time() - total_start
        print("\n" + "=" * 60)
        print(f"技术指标计算完成！")
        print(f"成功: {success_count}, 总耗时: {total_elapsed:.1f} 秒")
        print("=" * 60)
        
        return success_count
    
    @staticmethod
    def _next_day(date_str: str) -> str:
        """获取下一天"""
        date = datetime.datetime.strptime(date_str, '%Y%m%d')
        next_date = date + datetime.timedelta(days=1)
        return next_date.strftime('%Y%m%d')
