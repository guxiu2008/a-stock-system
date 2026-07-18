#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
卖出纪律系统 - 让长线与短线真正分家

核心设计哲学：
- 短线/波段：价格是朋友，严格执行机械交易纪律
- 成长模式：逻辑才是朋友，只看基本面和市场逻辑，不被价格洗下车
"""
import pandas as pd
import sqlite3
from typing import Dict, List, Tuple, Optional
from enum import Enum


class SellSignal(Enum):
    """卖出信号等级"""
    HOLD = "持有"
    REVIEW = "观察/重新评估"
    SELL_HALF = "减半"
    SELL_ALL = "全部卖出"


class SellDisciplineAnalyzer:
    """卖出纪律分析器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    # ==================== SHORT/SWING 模式：价格导向卖出 ====================
    
    def analyze_short_term(self, buy_price: float, current_price: float, 
                           hold_days: int, ma20: Optional[float] = None) -> Dict:
        """
        短线/波段模式卖出分析 - 严格执行价格纪律
        """
        pnl_pct = (current_price / buy_price - 1) * 100
        
        signals = []
        should_sell = SellSignal.HOLD
        sell_reason = ""
        sell_ratio = 0
        
        # ========== 止损 ==========
        if pnl_pct <= -7:
            should_sell = SellSignal.SELL_ALL
            sell_reason = "【硬止损触发】跌破买入价 -7%，无条件卖出"
            sell_ratio = 1.0
            signals.append(("止损", f"跌幅 {pnl_pct:.1f}%", "必须执行"))
        
        # MA20 止损增强
        if ma20 and current_price < ma20 and pnl_pct < 0:
            signals.append(("趋势止损", f"跌破MA20({ma20:.2f})", "建议减半"))
            if should_sell == SellSignal.HOLD:
                should_sell = SellSignal.REVIEW
        
        # ========== 止盈 ==========
        if pnl_pct >= 15:
            should_sell = SellSignal.SELL_ALL
            sell_reason = "【第二目标达成】涨幅超 15%，全部止盈"
            sell_ratio = 1.0
            signals.append(("止盈", f"涨幅 {pnl_pct:.1f}%", "第二目标达成"))
        elif pnl_pct >= 8:
            should_sell = SellSignal.SELL_HALF
            sell_reason = "【第一目标达成】涨幅超 8%，减半锁定利润"
            sell_ratio = 0.5
            signals.append(("止盈", f"涨幅 {pnl_pct:.1f}%", "第一目标达成，减半"))
        
        # ========== 时间止损 ==========
        if hold_days > 20 and pnl_pct < 5:
            signals.append(("时间止损", f"已持有 {hold_days} 天，涨幅不足 5%", "重新评估逻辑"))
            if should_sell == SellSignal.HOLD:
                should_sell = SellSignal.REVIEW
        
        return {
            "mode": "short_swing",
            "mode_name": "短线/波段模式",
            "buy_price": round(buy_price, 2),
            "current_price": round(current_price, 2),
            "pnl_pct": round(pnl_pct, 1),
            "hold_days": hold_days,
            "signal": should_sell.value,
            "sell_reason": sell_reason,
            "sell_ratio": sell_ratio,
            "details": signals,
            "discipline_summary": [
                "硬止损: 跌破 -7% → 全卖",
                "第一止盈: +8% → 卖50%",
                "第二止盈: +15% → 全卖",
                "时间止损: 持有20天不涨 → 重评"
            ]
        }
    
    # ==================== GROWTH 模式：逻辑导向卖出 ====================
    
    def _check_net_profit_bomb(self, ts_code: str) -> Dict:
        """
        ⚠️ 业绩暴雷检测 - 成长股死刑宣判线
        触发条件：扣非净利润单季度同比下滑超 30% OR 由正转负
        """
        try:
            conn = sqlite3.connect(self.db_path)
            # 取最近两个季度的扣非净利润数据（本季vs去年同期）
            query = """
                SELECT end_date, net_profit_ttm, net_profit_deduct_ttm
                FROM fact_financial_reports
                WHERE ts_code = ?
                  AND net_profit_deduct_ttm IS NOT NULL
                  AND report_type = 'regular'
                ORDER BY end_date DESC
                LIMIT 8
            """
            df = pd.read_sql(query, conn, params=(ts_code,))
            conn.close()
            
            if len(df) < 5:  # 数据不足（需要本季+4个季度前=去年同期）
                return {"is_bomb": False, "error": "数据不足"}
            
            # 最新季度扣非净利润
            latest_profit = df.iloc[0]['net_profit_deduct_ttm']
            # 去年同期扣非净利润（4个季度前）
            same_period_last_year = df.iloc[4]['net_profit_deduct_ttm']
            
            if same_period_last_year <= 0:
                # 去年亏损，今年盈利 = 不是暴雷
                return {"is_bomb": False, "trend": "扭亏为盈"}
            
            yoy_change_pct = (latest_profit / same_period_last_year - 1) * 100
            
            # 暴雷条件1：同比下滑 > 30%
            is_collapse = yoy_change_pct <= -30
            # 暴雷条件2：由盈利转亏损
            is_turn_negative = latest_profit <= 0 and same_period_last_year > 0
            
            is_bomb = is_collapse or is_turn_negative
            
            reason = ""
            if is_bomb:
                if is_turn_negative:
                    reason = f"扣非净利润由正转负，去年同期盈利 {same_period_last_year/1e8:.2f} 亿，本期亏损"
                else:
                    reason = f"扣非净利润同比下滑 {abs(yoy_change_pct):.1f}%，远超安全阈值 30%"
            
            return {
                "is_bomb": is_bomb,
                "yoy_change_pct": round(yoy_change_pct, 1),
                "latest_profit_100m": round(latest_profit / 1e8, 2),
                "same_period_last_year_100m": round(same_period_last_year / 1e8, 2),
                "reason": reason
            }
        except Exception as e:
            return {"is_bomb": False, "error": str(e)}
    
    def get_gross_margin_trend(self, ts_code: str, quarters: int = 4) -> Dict:
        """获取毛利率趋势，检测是否连续下滑"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT end_date, grossprofit_margin
                FROM fact_financial_reports
                WHERE ts_code = ?
                  AND grossprofit_margin IS NOT NULL
                ORDER BY end_date DESC
                LIMIT ?
            """
            df = pd.read_sql(query, conn, params=(ts_code, quarters))
            conn.close()
        except Exception as e:
            return {"error": str(e), "is_warning": False}
        
        if df.empty or len(df) < 2:
            return {"error": "数据不足", "is_warning": False}
        
        margins = df['grossprofit_margin'].tolist()
        dates = df['end_date'].tolist()
        
        # 计算连续下滑季度数
        consecutive_decline = 0
        for i in range(len(margins) - 1):
            if margins[i] < margins[i + 1]:
                consecutive_decline += 1
            else:
                break
        
        margin_history = list(zip(dates, [round(m, 2) for m in margins]))
        
        return {
            "margin_history": margin_history,
            "consecutive_decline": consecutive_decline,
            "is_warning": consecutive_decline >= 2,
            "trend": "下滑" if consecutive_decline >= 2 else "稳定/上升"
        }
    
    def get_policy_turn_signal(self, industry: str, lookback_days: int = 90) -> Dict:
        """检测行业政策是否发生根本性转向（支持→限制）"""
        try:
            conn = sqlite3.connect(self.db_path)
            neg_keywords = ['监管', '整顿', '规范', '限制', '去产能', '反垄断', '审查', '处罚']
            keyword_clause = ' OR '.join([f"title LIKE '%{kw}%' OR summary LIKE '%{kw}%'" for kw in neg_keywords])
            
            query = f"""
                SELECT COUNT(*) as neg_count, MAX(end_date) as latest_neg_date
                FROM fact_macro_narratives
                WHERE (sectors LIKE '%{industry}%' OR sectors IS NULL)
                  AND ({keyword_clause})
                  AND event_date >= strftime('%Y%m%d', date('now', '-{lookback_days} days'))
            """
            cursor = conn.execute(query)
            result = cursor.fetchone()
            conn.close()
            
            neg_count = result[0] or 0
            
            return {
                "negative_policy_count": neg_count,
                "latest_negative_date": result[1],
                "is_policy_turn": neg_count >= 3,
                "threshold": 3
            }
        except Exception as e:
            return {"error": str(e), "is_policy_turn": False}
    
    def get_industry_valuation_percentile(self, industry: str, ts_code: str = None) -> Dict:
        """
        获取行业估值分位 - 按行业类型智能选择估值指标
        稳定成长股（消费、医药等）：用PE分位
        强周期股（半导体、新能源、资源、制造等）：用PB分位
        """
        # 周期行业关键词列表
        CYCLICAL_INDUSTRIES = {
            '半导体', '芯片', '新能源', '光伏', '锂电池', '储能',
            '有色', '钢铁', '煤炭', '石油', '化工', '水泥', '建材',
            '航运', '港口', '船舶', '汽车', '机械', '制造', '周期',
            '证券', '券商', '保险', '银行'
        }
        
        # 判断行业类型
        is_cyclical = any(keyword in industry for keyword in CYCLICAL_INDUSTRIES)
        valuation_type = "PB" if is_cyclical else "PE"
        threshold = 90 if is_cyclical else 95
        
        try:
            conn = sqlite3.connect(self.db_path)
            # 根据行业类型选择PE或PB
            val_col = "pb" if is_cyclical else "pe"
            query = f"""
                SELECT {val_col}
                FROM fact_daily_quotes
                WHERE industry = ?
                  AND {val_col} IS NOT NULL
                  AND {val_col} > 0 AND {val_col} < 50
                ORDER BY trade_date DESC
                LIMIT 500
            """
            df = pd.read_sql(query, conn, params=(industry,))
            conn.close()
        except Exception as e:
            return {"error": str(e), "percentile": 50, "valuation_type": valuation_type}
        
        if df.empty:
            return {"error": f"无{valuation_type}数据", "percentile": 50, "valuation_type": valuation_type}
        
        current_val = df.iloc[0][val_col] if len(df) > 0 else 0
        percentile = (df[val_col] < current_val).sum() / len(df) * 100
        
        is_bubble = percentile >= threshold
        
        # 周期股额外提示：注意核心产品价格趋势
        extra_note = ""
        if is_cyclical:
            extra_note = "【周期股提醒】建议同时跟踪核心产品价格，跌破5日均线可减仓"
        
        return {
            "industry": industry,
            "valuation_type": valuation_type,
            "is_cyclical": is_cyclical,
            f"{val_col.lower()}_percentile": round(percentile, 1),
            "current_valuation": round(current_val, 2),
            "is_bubble_zone": is_bubble,
            "threshold": threshold,
            "interpretation": "极度泡沫" if is_bubble else ("高估" if percentile >= 80 else "正常"),
            "extra_note": extra_note
        }
    
    def get_margin_crowding(self, lookback_days: int = 30) -> Dict:
        """检测全市场杠杆资金拥挤度"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = f"""
                SELECT trade_date, rzye_market, rz_change_rate
                FROM fact_money_flow
                WHERE rzye_market IS NOT NULL
                ORDER BY trade_date DESC
                LIMIT {lookback_days + 30}
            """
            df = pd.read_sql(query, conn)
            conn.close()
        except Exception as e:
            return {"error": str(e), "is_crowded": False}
        
        if df.empty or len(df) < 30:
            return {"error": "数据不足", "is_crowded": False}
        
        df_sorted = df.sort_values('trade_date')
        rzye_now = df_sorted.iloc[-1]['rzye_market']
        rzye_30d_ago = df_sorted.iloc[-30]['rzye_market'] if len(df_sorted) >= 30 else rzye_now
        
        growth_rate = (rzye_now / rzye_30d_ago - 1) * 100 if rzye_30d_ago > 0 else 0
        is_crowded = growth_rate >= 15
        
        return {
            "margin_balance_30d_growth_pct": round(growth_rate, 1),
            "current_balance": rzye_now,
            "is_extremely_crowded": is_crowded,
            "threshold": 15,
            "interpretation": "极度拥挤" if is_crowded else ("偏热" if growth_rate >= 10 else "正常")
        }
    
    def analyze_growth_mode(self, ts_code: str, industry: str, buy_price: float = 0, 
                            current_price: float = 0, hold_days: int = 0) -> Dict:
        """
        成长模式卖出分析 - 逻辑证伪导向
        核心原则：不被价格波动洗下车，只在逻辑破位或估值泡沫时卖出
        """
        signals = []
        sell_level = 0  # 0=持有, 1=观察, 2=减半, 3=全卖
        sell_reasons = []
        
        # ========== 检查止损（逻辑证伪） ==========
        
        # ⚠️ 死刑宣判线：扣非净利润单季度同比下滑超 30% 或 由正转负 → 立即全卖
        # 成长股可以忍受股价腰斩，但绝不能忍受业绩暴雷
        profit_bomb = self._check_net_profit_bomb(ts_code)
        if profit_bomb.get("is_bomb"):
            signals.append(("💥 业绩暴雷", profit_bomb.get("reason", "净利润断崖式下滑"), "死刑宣判线触发"))
            sell_level = max(sell_level, 3)
            sell_reasons.append("业绩暴雷，成长逻辑彻底破位")
        
        margin_trend = self.get_gross_margin_trend(ts_code)
        if margin_trend.get("is_warning"):
            decline_q = margin_trend.get("consecutive_decline", 0)
            signals.append(("⚠️ 基本面恶化", f"毛利率连续 {decline_q} 个季度下滑", "逻辑破位信号"))
            sell_level = max(sell_level, 2)
            sell_reasons.append("毛利率连续下滑")
        
        policy_signal = self.get_policy_turn_signal(industry)
        if policy_signal.get("is_policy_turn"):
            signals.append(("⚠️ 政策转向", f"近90天出现 {policy_signal.get('negative_policy_count')} 条负面政策", "根本性转向风险"))
            sell_level = max(sell_level, 3)
            sell_reasons.append("产业政策根本性转向")
        
        # ========== 检查止盈（估值泡沫） ==========
        # 按行业类型智能选择估值指标：成长股用PE，周期股用PB
        val_percentile = self.get_industry_valuation_percentile(industry, ts_code)
        if val_percentile.get("is_bubble_zone"):
            val_type = val_percentile.get("valuation_type", "PE")
            pct_key = f"{val_type.lower()}_percentile"
            threshold = val_percentile.get("threshold", 95)
            signals.append((
                "⚠️ 估值泡沫", 
                f"行业{val_type}分位 {val_percentile.get(pct_key)}% ≥ {threshold}%", 
                val_percentile.get("interpretation", "历史极值区")
            ))
            sell_level = max(sell_level, 2)
            # 根据行业类型给出不同的卖出理由
            if val_percentile.get("is_cyclical"):
                sell_reasons.append(f"周期行业{val_type}估值进入历史极值区，建议同时跟踪核心产品价格趋势")
            else:
                sell_reasons.append("行业估值进入历史泡沫区")
            # 附加周期股特殊提示
            extra_note = val_percentile.get("extra_note")
            if extra_note:
                signals.append(("💡 周期股提示", extra_note, "建议额外跟踪"))
        
        margin_crowd = self.get_margin_crowding()
        if margin_crowd.get("is_extremely_crowded"):
            signals.append(("⚠️ 资金拥挤", f"全市场融资余额月增速 {margin_crowd.get('margin_balance_30d_growth_pct')}%", "情绪见顶信号"))
            sell_level = max(sell_level, 1)
            if sell_level == 0:
                sell_reasons.append("杠杆资金极度拥挤，注意风险")
        
        # ========== 生成最终建议 ==========
        
        if sell_level >= 3:
            final_signal = SellSignal.SELL_ALL
            sell_ratio = 1.0
            summary_reason = "【逻辑破位】成长逻辑已被证伪，建议全部卖出"
        elif sell_level >= 2:
            final_signal = SellSignal.SELL_HALF
            sell_ratio = 0.5
            summary_reason = "【信号预警】出现负面信号，建议减半观察"
        elif sell_level >= 1:
            final_signal = SellSignal.REVIEW
            sell_ratio = 0.0
            summary_reason = "【观察提醒】有潜在风险信号，建议密切跟踪"
        else:
            final_signal = SellSignal.HOLD
            sell_ratio = 0.0
            summary_reason = "【继续持有】成长逻辑未变，估值合理，坚定持有"
        
        pnl_pct = (current_price / buy_price - 1) * 100 if buy_price > 0 and current_price > 0 else 0
        
        return {
            "mode": "growth",
            "mode_name": "成长模式",
            "core_principle": "逻辑证伪卖出，不因短期波动下车",
            "ts_code": ts_code,
            "industry": industry,
            "current_price": round(current_price, 2),
            "pnl_pct": round(pnl_pct, 1),
            "hold_days": hold_days,
            "signal": final_signal.value,
            "summary_reason": summary_reason,
            "sell_ratio": sell_ratio,
            "details": signals,
            "margin_trend": margin_trend,
            "policy_signal": policy_signal,
            "valuation_percentile": val_percentile,
            "margin_crowding": margin_crowd,
            "discipline_summary": [
                "逻辑止损1: 毛利率连续2季下滑 → 减半",
                "逻辑止损2: 产业政策根本性转向 → 全卖",
                "估值止盈1: 行业PE分位≥95% → 减半",
                "估值止盈2: 融资余额月增≥15% → 观察",
                "核心原则: 不看短期涨跌，只看逻辑和估值"
            ]
        }
