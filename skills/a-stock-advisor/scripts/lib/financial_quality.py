#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务质量分析 - 升级版基本面打分
核心思想：从"看历史数据"升级到"看数据质量"
避免周期股顶峰陷阱，识别真正的高质量公司

财务三问：
1. ROE 稳定性 (2分)：过去3年 ROE 是否连续 ≥12%？
2. 现金流含金量 (2分)：经营性现金流 / 净利润 ≥ 1.0？
3. 负债安全边际 (1分)：资产负债率是否低于行业平均？
"""
import pandas as pd
import sqlite3
from typing import Dict, Tuple, Optional


class FinancialQualityAnalyzer:
    """财务质量分析器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    # ==================== ROE 稳定性检测 ====================
    
    def get_roe_stability(self, ts_code: str, years: int = 3, min_roe: float = 12.0) -> Tuple[bool, float, Dict]:
        """
        检测 ROE 稳定性：过去 N 年 ROE 是否连续 ≥ min_roe
        
        Args:
            ts_code: 股票代码
            years: 回看年数
            min_roe: 最低ROE要求
            
        Returns:
            (是否达标, 平均ROE, 详细数据字典)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT end_date, roe, report_type
                FROM fact_financial_reports
                WHERE ts_code = ?
                  AND report_type = '年报'
                  AND roe IS NOT NULL
                ORDER BY end_date DESC
                LIMIT ?
            """
            df = pd.read_sql(query, conn, params=(ts_code, years))
            conn.close()
        except Exception as e:
            return False, 0.0, {"error": str(e)}
        
        if df.empty or len(df) < years:
            return False, 0.0, {"error": f"数据不足，仅{len(df)}年年报"}
        
        # 检查是否连续达标
        roe_values = df['roe'].tolist()
        avg_roe = sum(roe_values) / len(roe_values)
        all_above_min = all(r >= min_roe for r in roe_values)
        
        detail = {
            "years_available": len(df),
            "roe_list": [round(r, 2) for r in roe_values],
            "avg_roe": round(avg_roe, 2),
            "min_roe_required": min_roe,
            "all_above_threshold": all_above_min
        }
        
        return all_above_min, avg_roe, detail
    
    def score_roe_stability(self, ts_code: str, max_score: int = 2) -> Tuple[int, Dict]:
        """
        ROE 稳定性打分（满分2分）
        
        评分规则：
        - 连续3年 ROE ≥ 12% → +2分
        - 连续2年 ROE ≥ 10% → +1分
        - 否则 0分
        """
        # 严格标准：连续3年 ≥12%
        strict_pass, _, strict_detail = self.get_roe_stability(ts_code, years=3, min_roe=12.0)
        if strict_pass:
            return 2, {**strict_detail, "level": "优秀 - 连续3年稳定高回报"}
        
        # 宽松标准：连续2年 ≥10%
        loose_pass, _, loose_detail = self.get_roe_stability(ts_code, years=2, min_roe=10.0)
        if loose_pass:
            return 1, {**loose_detail, "level": "良好 - 连续2年稳定回报"}
        
        return 0, {**strict_detail, "level": "一般 - ROE稳定性不足"}
    
    # ==================== 现金流含金量检测 ====================
    
    def get_cash_flow_quality(self, ts_code: str) -> Tuple[float, Dict]:
        """
        计算现金流含金量：经营性现金流净额 / 净利润
        
        理想值 ≥ 1.0（赚的是真钱）
        危险值 < 0.7（利润含金量低，可能有水分）
        """
        try:
            conn = sqlite3.connect(self.db_path)
            # 取最近1年年报数据
            query = """
                SELECT end_date, ncf_from_oa, net_profit
                FROM fact_financial_reports
                WHERE ts_code = ?
                  AND report_type = '年报'
                  AND ncf_from_oa IS NOT NULL
                  AND net_profit IS NOT NULL
                  AND net_profit > 0
                ORDER BY end_date DESC
                LIMIT 1
            """
            df = pd.read_sql(query, conn, params=(ts_code,))
            conn.close()
        except Exception as e:
            return 0.0, {"error": str(e)}
        
        if df.empty:
            return 0.0, {"error": "无有效现金流数据"}
        
        row = df.iloc[0]
        ncf = row['ncf_from_oa']
        profit = row['net_profit']
        
        if profit <= 0:
            return 0.0, {"error": "净利润为负，无法计算"}
        
        ratio = ncf / profit
        
        detail = {
            "end_date": row['end_date'],
            "operating_cashflow": round(ncf, 2),
            "net_profit": round(profit, 2),
            "cashflow_ratio": round(ratio, 2)
        }
        
        return ratio, detail
    
    def score_cash_flow(self, ts_code: str, max_score: int = 2) -> Tuple[int, Dict]:
        """
        现金流含金量打分（满分2分）
        
        评分规则：
        - 现金流/净利润 ≥ 1.0 → +2分（赚的是真钱）
        - 0.7 ≤ 现金流/净利润 < 1.0 → +1分（基本合格）
        - 现金流/净利润 < 0.7 → -2分（利润有水分，重扣分）
        """
        ratio, detail = self.get_cash_flow_quality(ts_code)
        
        if ratio >= 1.0:
            return 2, {**detail, "level": "优秀 - 利润含金量高，赚的是真钱"}
        elif ratio >= 0.7:
            return 1, {**detail, "level": "良好 - 利润含金量基本合格"}
        elif ratio > 0:
            return -2, {**detail, "level": "危险 - 利润含金量低，可能有水分"}
        else:
            return -2, {**detail, "level": "危险 - 经营现金流为负"}
    
    # ==================== 负债安全边际检测 ====================
    
    def get_industry_avg_debt_ratio(self, industry: str, top_n_stocks: int = 50) -> float:
        """
        获取行业平均资产负债率
        
        Args:
            industry: 行业名称
            top_n_stocks: 用行业内前N只股票的平均值
            
        Returns:
            行业平均资产负债率（%）
        """
        try:
            conn = sqlite3.connect(self.db_path)
            # 先获取行业内股票列表
            # 注意：这里简化处理，实际需要行业映射表
            # 暂时用简单的方法：从 daily quotes 中获取行业股票
            query = """
                SELECT DISTINCT ts_code
                FROM fact_daily_quotes
                WHERE industry = ?
                LIMIT ?
            """
            df_inds = pd.read_sql(query, conn, params=(industry, top_n_stocks))
            
            if df_inds.empty:
                conn.close()
                return 50.0  # 默认平均值
            
            codes = ','.join([f"'{c}'" for c in df_inds['ts_code'].tolist()])
            
            # 获取这些股票的最新负债率
            query = f"""
                SELECT debt_to_assets
                FROM fact_financial_reports
                WHERE ts_code IN ({codes})
                  AND report_type = '年报'
                  AND debt_to_assets IS NOT NULL
                GROUP BY ts_code
                HAVING MAX(end_date)
            """
            df_debt = pd.read_sql(query, conn)
            conn.close()
            
            if df_debt.empty:
                return 50.0
            
            return float(df_debt['debt_to_assets'].mean())
        except Exception as e:
            return 50.0  # 出错返回默认值
    
    def get_debt_safety(self, ts_code: str, industry: Optional[str] = None) -> Tuple[bool, float, Dict]:
        """
        检测负债安全边际：资产负债率是否低于行业平均
        
        Returns:
            (是否低于行业平均, 公司负债率, 详细数据)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT end_date, debt_to_assets
                FROM fact_financial_reports
                WHERE ts_code = ?
                  AND report_type = '年报'
                  AND debt_to_assets IS NOT NULL
                ORDER BY end_date DESC
                LIMIT 1
            """
            df = pd.read_sql(query, conn, params=(ts_code,))
            conn.close()
        except Exception as e:
            return True, 50.0, {"error": str(e)}  # 出错默认安全
        
        if df.empty:
            return True, 50.0, {"error": "无负债数据"}
        
        debt_ratio = float(df.iloc[0]['debt_to_assets'])
        
        # 获取行业平均（简化处理：如果没传行业，用50%作为通用基准）
        industry_avg = 50.0
        if industry:
            # 注意：完整实现需要行业映射，这里简化处理
            # 不同行业有不同合理负债率：银行>80%, 地产>70%, 制造业<50%
            # 这里用简单的分类阈值代替
            if any(kw in industry for kw in ['银行', '保险', '证券']):
                industry_avg = 85.0
            elif any(kw in industry for kw in ['地产', '房地产']):
                industry_avg = 70.0
            elif any(kw in industry for kw in ['建筑', '施工']):
                industry_avg = 65.0
            else:
                industry_avg = 50.0
        
        is_safe = debt_ratio < industry_avg
        
        detail = {
            "end_date": df.iloc[0]['end_date'],
            "company_debt_ratio": round(debt_ratio, 2),
            "industry_avg_debt": round(industry_avg, 2),
            "debt_diff": round(debt_ratio - industry_avg, 2)
        }
        
        return is_safe, debt_ratio, detail
    
    def score_debt_safety(self, ts_code: str, industry: Optional[str] = None, 
                          max_score: int = 1) -> Tuple[int, Dict]:
        """
        负债安全边际打分（满分1分）
        
        评分规则：
        - 资产负债率 < 行业平均 → +1分（安全）
        - 否则 → 0分
        """
        is_safe, _, detail = self.get_debt_safety(ts_code, industry)
        
        if is_safe:
            return 1, {**detail, "level": "安全 - 负债率低于行业平均"}
        else:
            return 0, {**detail, "level": "一般 - 负债率高于或接近行业平均"}
    
    # ==================== 综合财务质量打分 ====================
    
    def score_fundamental_quality(self, ts_code: str, industry: Optional[str] = None) -> Tuple[int, Dict]:
        """
        升级版基本面综合打分（满分5分）
        
        财务三问：
        1. ROE 稳定性 (2分)：过去3年 ROE 是否连续 ≥ 12%
        2. 现金流含金量 (2分)：经营性现金流 / 净利润 ≥ 1.0
        3. 负债安全边际 (1分)：资产负债率是否低于行业平均
        
        Returns:
            (总分, 详细分数字典)
        """
        scores = {}
        details = {}
        
        # 1. ROE 稳定性 (2分)
        roe_score, roe_detail = self.score_roe_stability(ts_code)
        scores['roe_stability'] = roe_score
        details['roe_stability'] = roe_detail
        
        # 2. 现金流含金量 (2分)
        cf_score, cf_detail = self.score_cash_flow(ts_code)
        scores['cash_flow'] = cf_score
        details['cash_flow'] = cf_detail
        
        # 3. 负债安全边际 (1分)
        debt_score, debt_detail = self.score_debt_safety(ts_code, industry)
        scores['debt_safety'] = debt_score
        details['debt_safety'] = debt_detail
        
        # 计算总分（注意现金流可能是负分）
        total = roe_score + cf_score + debt_score
        # 最低分不低于 0（避免极端负分影响太大）
        total = max(0, total)
        
        details['total_score'] = total
        details['max_score'] = 5
        
        # 评级
        if total >= 4:
            details['rating'] = 'A+ - 财务质量优秀'
        elif total >= 3:
            details['rating'] = 'A - 财务质量良好'
        elif total >= 2:
            details['rating'] = 'B - 财务质量一般'
        elif total >= 1:
            details['rating'] = 'C - 财务质量偏弱'
        else:
            details['rating'] = 'D - 财务质量较差'
        
        return total, details
