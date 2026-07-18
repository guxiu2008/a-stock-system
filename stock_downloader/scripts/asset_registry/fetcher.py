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
        获取概念分类。
        
        不再调用 Tushare Pro 已不可用的 concept/concept_detail 接口。
        批量更新优先使用 DC 东方财富板块接口；THS 同花顺 ths_member
        接口需要按板块逐个查询且频率限制很低，不再作为批量更新来源，
        避免在 update-all 时产生大量无效调用并触发频率超限。
        
        Returns:
            概念分类DataFrame。
        """
        print("正在获取概念分类...")
        
        df_boards = self._fetch_dc_concept_classify()
        if not df_boards.empty:
            return df_boards
        
        return self._fetch_ths_concept_classify()
    
    def _fetch_ths_concept_classify(self) -> pd.DataFrame:
        """
        使用 Tushare Pro 同花顺概念板块接口获取概念分类。
        
        ths_index 只能获取板块列表，不能直接得到股票-概念映射；
        ths_member 需要按每个板块逐次调用，且普通权限频率限制很低。
        因此批量更新时跳过 ths_member，避免大量调用和频率超限。
        
        Returns:
            概念分类DataFrame。
        """
        print("跳过 THS 同花顺概念板块成分股批量获取：ths_member 需按板块逐个调用且频率限制较低")
        return pd.DataFrame()
    
    def _fetch_dc_concept_classify(self) -> pd.DataFrame:
        """
        使用 Tushare Pro 东方财富板块接口获取概念分类。
        
        Returns:
            概念分类DataFrame。
        """
        print("正在使用 DC 东方财富板块接口获取概念分类...")
        
        try:
            time.sleep(1)
            df_concepts = self.pro.query(
                'dc_index',
                fields='ts_code,name'
            )
        except Exception as e:
            print(f"DC 东方财富板块列表获取失败: {e}")
            return pd.DataFrame()
        
        return self._fetch_board_members(
            df_concepts=df_concepts,
            list_api_name='DC 东方财富板块',
            member_api_name='dc_member',
            member_fields='ts_code,con_code,name'
        )
    
    def _fetch_board_members(
        self,
        df_concepts: pd.DataFrame,
        list_api_name: str,
        member_api_name: str,
        member_fields: str
    ) -> pd.DataFrame:
        """
        根据板块列表获取板块成分股并标准化为概念分类格式。
        
        Args:
            df_concepts: 板块列表DataFrame。
            list_api_name: 板块列表接口显示名称。
            member_api_name: 成分股接口名。
            member_fields: 成分股接口字段。
        
        Returns:
            概念分类DataFrame。
        """
        if df_concepts.empty:
            print(f"{list_api_name}接口未获取到板块列表")
            return pd.DataFrame()
        
        required_columns = {'ts_code', 'name'}
        if not required_columns.issubset(df_concepts.columns):
            print(f"{list_api_name}接口返回字段异常: {list(df_concepts.columns)}")
            return pd.DataFrame()
        
        all_data = []
        hit_rate_limit = False
        total_count = len(df_concepts)
        success_count = 0
        
        print(f"开始获取 {total_count} 个板块的成分股...")
        print("-" * 60)
        
        for idx, row in df_concepts.iterrows():
            concept_code = row['ts_code']
            concept_name = row['name']
            
            # 显示进度
            progress_pct = ((idx + 1) / total_count) * 100
            print(f"\r{' ' * 60}\r", end="")
            print(f"进度: [{idx + 1}/{total_count}] {progress_pct:.1f}% | {concept_name}", end="", flush=True)
            
            try:
                time.sleep(0.2)  # API调用间隔0.2秒，每分钟大约300次，避免触发500次限制
                df_cons = self.pro.query(
                    member_api_name,
                    ts_code=concept_code,
                    fields=member_fields
                )
            except Exception as e:
                error_msg = str(e)
                print(f"\n获取 {concept_name} 成分股失败: {error_msg}")
                if self._is_tushare_rate_limit_error(error_msg):
                    hit_rate_limit = True
                    print(f"{member_api_name} 已触发频率限制，停止继续请求")
                    break
                continue
            
            if not df_cons.empty:
                df_standard = self._normalize_board_members(df_cons, concept_code, concept_name)
                if not df_standard.empty:
                    all_data.append(df_standard)
                    success_count += 1
        
        # 清除进度条
        print(f"\r{' ' * 60}\r", end="")
        print("-" * 60)
        
        if hit_rate_limit:
            print(f"{list_api_name}成分股同步因频率限制中断")
            if not all_data:
                return pd.DataFrame()
        
        if not all_data:
            print(f"{list_api_name}接口未获取到有效板块成分股")
            print(f"统计: 成功 {success_count}/{total_count} 个板块")
            return pd.DataFrame()
        
        print(f"统计: 成功 {success_count}/{total_count} 个板块")
        
        df_result = pd.concat(all_data, ignore_index=True)
        df_result = df_result[df_result['ts_code'].notna() & (df_result['ts_code'] != '')]
        df_result = df_result.drop_duplicates(subset=['ts_code', 'concept_code'], keep='last')
        return df_result
    
    @staticmethod
    def _is_tushare_rate_limit_error(error_msg: str) -> bool:
        """
        判断 Tushare 错误信息是否为接口频率限制。
        
        Args:
            error_msg: 异常信息。
        
        Returns:
            是否为频率限制错误。
        """
        rate_limit_keywords = ('频率超限', '每分钟', '每天', '访问接口')
        return any(keyword in error_msg for keyword in rate_limit_keywords)
    
    def _normalize_batch_board_members(
        self,
        df_cons: pd.DataFrame,
        concept_map: dict
    ) -> pd.DataFrame:
        """
        标准化批量板块成分股接口返回结果。
        
        Args:
            df_cons: 成分股DataFrame（包含多个板块的数据）。
            concept_map: 概念代码到名称的映射字典。
        
        Returns:
            标准化后的概念分类DataFrame。
        """
        if df_cons.empty:
            return pd.DataFrame()
        
        df_cons = df_cons.copy()
        
        # 转换股票代码列
        if 'con_code' in df_cons.columns:
            df_cons['ts_code'] = df_cons['con_code']
        elif 'code' in df_cons.columns:
            df_cons['ts_code'] = df_cons['code']
        elif 'ts_code' not in df_cons.columns:
            print(f"批量成分股字段异常: {list(df_cons.columns)}")
            return pd.DataFrame()
        
        # 添加概念代码和名称
        result_data = []
        for _, row in df_cons.iterrows():
            concept_code = row.get('ts_code')  # 注意：这里的ts_code是板块代码
            if concept_code and concept_code in concept_map:
                concept_name = concept_map[concept_code]
                # 构建单条记录
                result_data.append({
                    'ts_code': row['ts_code'] if 'con_code' not in df_cons.columns else row['con_code'],
                    'concept_code': concept_code,
                    'concept_name': concept_name,
                    'update_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        
        return pd.DataFrame(result_data) if result_data else pd.DataFrame()
    
    def _normalize_board_members(
        self,
        df_cons: pd.DataFrame,
        concept_code: str,
        concept_name: str
    ) -> pd.DataFrame:
        """
        标准化新版板块成分股接口返回结果。
        
        Args:
            df_cons: 成分股DataFrame。
            concept_code: 板块代码。
            concept_name: 板块名称。
        
        Returns:
            标准化后的概念分类DataFrame。
        """
        if df_cons.empty:
            return pd.DataFrame()
        
        df_cons = df_cons.copy()
        if 'con_code' in df_cons.columns:
            df_cons['ts_code'] = df_cons['con_code']
        elif 'code' in df_cons.columns:
            df_cons['ts_code'] = df_cons['code']
        elif 'ts_code' not in df_cons.columns:
            print(f"板块 {concept_name} 成分股字段异常: {list(df_cons.columns)}")
            return pd.DataFrame()
        
        df_cons['concept_code'] = concept_code
        df_cons['concept_name'] = concept_name
        df_cons['update_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return df_cons[['ts_code', 'concept_code', 'concept_name', 'update_time']]
    
    def _fetch_symbol_ts_code_map(self) -> dict:
        """
        获取股票 symbol 到 ts_code 的映射。
        
        Returns:
            symbol 到 ts_code 的映射字典。
        """
        try:
            time.sleep(1)  # API调用间隔1秒
            df_stock = self.pro.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,symbol'
            )
        except Exception as e:
            print(f"获取股票代码映射失败，将按代码规则推断交易所后缀: {e}")
            return {}
        
        if df_stock.empty:
            return {}
        
        df_stock['symbol'] = df_stock['symbol'].astype(str).str.zfill(6)
        return dict(zip(df_stock['symbol'], df_stock['ts_code']))
    
    @staticmethod
    def _infer_ts_code(code: str) -> Optional[str]:
        """
        根据股票代码推断 Tushare ts_code。
        
        Args:
            code: 6位股票代码。
        
        Returns:
            推断出的 ts_code，无法推断时返回 None。
        """
        if code.startswith('6'):
            return f"{code}.SH"
        if code.startswith(('0', '3')):
            return f"{code}.SZ"
        if code.startswith(('4', '8', '9')):
            return f"{code}.BJ"
        return None
