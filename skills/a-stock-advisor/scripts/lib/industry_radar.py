#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行业雷达 - 升级版板块筛选工具
核心功能：
1. 行业拥挤度检测（防止追涨杀跌）
2. 政策共振检测（寻找逆向布局机会）
3. 多模式行业筛选策略
"""
import pandas as pd
import sqlite3
from typing import List, Dict, Optional
from collections import Counter
from datetime import datetime, timedelta


class IndustryRadar:
    """行业雷达核心类"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    # ==================== 行业拥挤度检测 ====================
    
    def get_industry_crowding_score(self, df: pd.DataFrame, lookback_days: int = 10) -> Dict[str, float]:
        """
        计算行业拥挤度（用成交量变化代替融资余额）
        原理：近 N 日成交量激增意味着散户涌入，可能是高位接盘信号
        
        Args:
            df: 股票行情数据，需要包含 industry, vol 列
            lookback_days: 回看天数
            
        Returns:
            {行业名称: 拥挤度分数(>1表示激增)}
        """
        if df.empty or 'industry' not in df.columns or 'vol' not in df.columns:
            return {}
        
        # 按行业聚合成交量
        industry_vol = df.groupby('industry')['vol'].agg(['mean', 'std', 'count']).reset_index()
        industry_vol.columns = ['industry', 'vol_mean', 'vol_std', 'stock_count']
        
        # 计算拥挤度：当前成交量相对历史均值的倍数
        # 这里简化处理，用当前截面数据的波动率作为代理
        crowding = {}
        for _, row in industry_vol.iterrows():
            # 变异系数作为拥挤度代理
            if row['vol_mean'] > 0 and row['stock_count'] >= 3:
                cv = row['vol_std'] / row['vol_mean'] if row['vol_std'] > 0 else 0
                crowding[row['industry']] = cv
        
        return crowding
    
    def filter_crowded_industries(self, industries: List[str], crowding_scores: Dict[str, float], 
                                  threshold: float = 0.3) -> List[str]:
        """
        过滤掉拥挤度过高的行业
        
        Args:
            industries: 候选行业列表
            crowding_scores: 拥挤度分数
            threshold: 拥挤度阈值（默认0.3，即波动超过均值30%）
            
        Returns:
            过滤后的行业列表
        """
        filtered = []
        for ind in industries:
            score = crowding_scores.get(ind, 0)
            if score <= threshold:
                filtered.append(ind)
        
        return filtered
    
    # ==================== 政策共振检测 ====================
    
    def get_policy_resonance(self, lookback_days: int = 7, top_n: int = 10) -> Dict[str, int]:
        """
        检测近 N 日政策关键词密度，找出政策共振行业
        
        Args:
            lookback_days: 回看天数
            top_n: 返回前 N 个行业
            
        Returns:
            {行业名称: 政策提及次数}
        """
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y%m%d")
        
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT sectors, keywords, importance
                FROM fact_macro_narratives
                WHERE event_date >= ? AND event_date <= ?
                ORDER BY importance DESC
            """
            df = pd.read_sql(query, conn, params=(start_date, end_date))
            conn.close()
        except Exception as e:
            print(f"查询政策数据失败: {e}")
            return {}
        
        if df.empty:
            return {}
        
        # 解析 sectors 字段（逗号分隔的行业名称）
        industry_counter = Counter()
        
        for _, row in df.iterrows():
            sectors = str(row['sectors']).strip()
            if not sectors or sectors == 'nan':
                continue
            
            # 分割多个行业
            sector_list = [s.strip() for s in sectors.split(',') if s.strip()]
            
            # 按重要性加权
            weight = row.get('importance', 1) or 1
            for sector in sector_list:
                industry_counter[sector] += weight
        
        # 返回排序后的结果
        return dict(industry_counter.most_common(top_n))
    
    def get_oversold_industries(self, df: pd.DataFrame, top_n: int = 10) -> List[str]:
        """
        找出近60日跌幅最大的行业（中线超跌）
        
        Args:
            df: 股票行情数据，需要包含 industry, ret_60d_pct 列
            top_n: 返回前 N 个超跌行业
            
        Returns:
            超跌行业列表
        """
        if df.empty or 'industry' not in df.columns or 'ret_60d_pct' not in df.columns:
            return []
        
        # 按行业聚合60日收益率
        industry_ret = df.groupby('industry')['ret_60d_pct'].agg(['mean', 'count']).reset_index()
        industry_ret = industry_ret[industry_ret['count'] >= 5]  # 只考虑股票数量足够的行业
        
        # 按涨幅从小到大排序（跌幅最大在前）
        industry_ret = industry_ret.sort_values('mean', ascending=True).reset_index(drop=True)
        
        return industry_ret.head(top_n)['industry'].tolist()
    
    def get_policy_resonance_oversold(self, df: pd.DataFrame, lookback_days: int = 7,
                                       top_oversold: int = 10, top_policy: int = 5) -> List[str]:
        """
        成长模式专属：寻找"中线超跌 + 政策吹风"的行业（真正的逆向布局）
        
        Args:
            df: 股票行情数据
            lookback_days: 政策回看天数
            top_oversold: 超跌行业数量
            top_policy: 政策密集行业数量
            
        Returns:
            同时满足两个条件的行业列表
        """
        # 1. 找出近60日跌幅前N的行业（中线超跌）
        oversold = self.get_oversold_industries(df, top_oversold)
        
        # 2. 找出近7日政策关键词密度前N的行业
        policy = self.get_policy_resonance(lookback_days, top_policy)
        policy_industries = list(policy.keys())
        
        # 3. 交集 = 超跌 + 政策吹风
        resonance = [ind for ind in oversold if ind in policy_industries]
        
        return resonance
    
    # ==================== 模式专属行业筛选 ====================
    
    def select_industries_short(self, df: pd.DataFrame, rank_range: tuple = (3, 12),
                                max_3d_pct: float = 15.0, crowding_threshold: float = 0.3) -> List[str]:
        """
        短线模式行业筛选：动量排名 + 拥挤度过滤
        
        Args:
            df: 股票行情数据
            rank_range: 排名范围 (start, end)
            max_3d_pct: 最大3日涨幅（过热过滤）
            crowding_threshold: 拥挤度阈值
            
        Returns:
            行业列表
        """
        if df.empty or 'cum_3d_pct' not in df.columns or 'industry' not in df.columns:
            return []
        
        # 1. 基础动量筛选
        ind_perf = df.groupby("industry")["cum_3d_pct"].agg(["mean", "count"]).reset_index()
        ind_perf = ind_perf[ind_perf["count"] >= 5]
        ind_perf = ind_perf[ind_perf["mean"] <= max_3d_pct]
        ind_perf = ind_perf.sort_values("mean", ascending=False).reset_index(drop=True)
        
        if ind_perf.empty:
            return []
        
        # 2. 取排名范围
        lo, hi = rank_range
        if len(ind_perf) >= hi:
            candidate_inds = ind_perf.iloc[lo - 1:hi]["industry"].tolist()
        else:
            candidate_inds = ind_perf.iloc[max(0, lo - 1):]["industry"].tolist()
        
        # 3. 拥挤度过滤（防止散户高位接盘）
        crowding_scores = self.get_industry_crowding_score(df)
        filtered_inds = self.filter_crowded_industries(candidate_inds, crowding_scores, crowding_threshold)
        
        return filtered_inds
    
    def select_industries_swing(self, df: pd.DataFrame, rank_range: tuple = (3, 15),
                                 crowding_threshold: float = 0.25) -> List[str]:
        """
        波段模式行业筛选：中期强度 + 拥挤度过滤
        
        Args:
            df: 股票行情数据
            rank_range: 排名范围
            crowding_threshold: 拥挤度阈值
            
        Returns:
            行业列表
        """
        if df.empty or 'industry_strength' not in df.columns:
            return []
        
        # 1. 中期强度排名
        ind_perf = df.groupby("industry").agg(
            mean=("industry_strength", "mean"),
            count=("industry", "count"),
        ).reset_index()
        ind_perf = ind_perf[ind_perf["count"] >= 5]
        ind_perf = ind_perf.sort_values("mean", ascending=False).reset_index(drop=True)
        
        if ind_perf.empty:
            return []
        
        # 2. 取排名范围
        lo, hi = rank_range
        if len(ind_perf) >= hi:
            candidate_inds = ind_perf.iloc[lo - 1:hi]["industry"].tolist()
        else:
            candidate_inds = ind_perf.iloc[max(0, lo - 1):]["industry"].tolist()
        
        # 3. 拥挤度过滤
        crowding_scores = self.get_industry_crowding_score(df)
        filtered_inds = self.filter_crowded_industries(candidate_inds, crowding_scores, crowding_threshold)
        
        return filtered_inds
    
    def select_industries_growth(self, df: pd.DataFrame, lookback_days: int = 7,
                                 top_oversold: int = 15, top_policy: int = 8) -> List[str]:
        """
        成长模式行业筛选：中线超跌 + 政策共振（逆向布局）
        如果没有政策共振数据，降级为基本面排名靠前的行业
        
        Args:
            df: 股票行情数据
            lookback_days: 政策回看天数
            top_oversold: 超跌行业数量
            top_policy: 政策密集行业数量
            
        Returns:
            行业列表
        """
        # 1. 尝试政策共振逆向布局
        resonance_inds = self.get_policy_resonance_oversold(df, lookback_days, top_oversold, top_policy)
        
        if len(resonance_inds) >= 3:
            return resonance_inds
        
        # 2. 降级方案：如果政策数据不足，用基本面排名 + 适度超跌
        if 'growth_score' in df.columns:
            ind_perf = df.groupby("industry").agg(
                mean_growth=("growth_score", "mean"),
                mean_roe=("latest_roe", "mean"),
                count=("industry", "count"),
            ).reset_index()
            ind_perf = ind_perf[ind_perf["count"] >= 5]
            ind_perf = ind_perf.sort_values("mean_growth", ascending=False).reset_index(drop=True)
            return ind_perf.head(15)["industry"].tolist()
        
        return []
