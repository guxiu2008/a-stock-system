#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大盘动态仓位控制阻尼器

核心设计思想：
- 不看单一的上证指数（容易被权重股操纵）
- 用全市场均线多头排列比例作为真正的大盘温度
- 平滑、真实、反映大多数股票的实际状态

仓位计算公式：
- 全市场股票站上MA20比例 ≥ 60% → 上升趋势 → 仓位 80%
- 全市场股票站上MA20比例 20%~60% → 震荡市 → 仓位 30%~50%
- 全市场股票站上MA20比例 < 20% → 下跌趋势 → 仓位 20%
"""
import pandas as pd
import sqlite3
from typing import Dict, Tuple, Optional
from enum import Enum


class MarketTrend(Enum):
    """市场趋势定义"""
    BULL = "上升趋势"
    SHOCK = "震荡市"
    BEAR = "下跌趋势"


class MarketDamper:
    """大盘阻尼器：用全市场均线多头比例动态控制仓位"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_ma20_breadth(self, date: Optional[str] = None) -> Dict:
        """
        计算全市场 MA20 均线广度：站上 MA20 的股票比例
        
        这是比上证指数更可靠的大盘温度指标：
        - ≥ 60% → 全面牛市，绝大多数股票在上升
        - 20%~60% → 震荡市，结构化行情
        - < 20% → 全面熊市，绝大多数股票在下跌
        """
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 先获取最新交易日期（如果没指定）
            if not date:
                date_query = """
                    SELECT MAX(trade_date) FROM fact_daily_quotes
                """
                cursor = conn.execute(date_query)
                date = str(cursor.fetchone()[0])
            
            # 查询全市场股票 MA20 状态
            query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN close >= ma20 THEN 1 ELSE 0 END) as above_ma20,
                    SUM(CASE WHEN close < ma20 THEN 1 ELSE 0 END) as below_ma20
                FROM fact_daily_quotes
                WHERE trade_date = ?
                  AND ma20 IS NOT NULL
                  AND close > 0
            """
            df = pd.read_sql(query, conn, params=(date,))
            conn.close()
            
            if df.empty:
                return {"error": "无数据", "date": date}
            
            total = int(df.iloc[0]['total'])
            above = int(df.iloc[0]['above_ma20'])
            below = int(df.iloc[0]['below_ma20'])
            
            if total == 0:
                return {"error": "总股票数为0", "date": date}
            
            above_pct = round(above / total * 100, 1)
            below_pct = round(below / total * 100, 1)
            
            # 判断趋势
            if above_pct >= 60:
                trend = MarketTrend.BULL
                position_pct = 80
                confidence = "高"
            elif above_pct >= 20:
                trend = MarketTrend.SHOCK
                # 震荡市内线性插值：20%→30%仓位，60%→50%仓位
                position_pct = int(30 + (above_pct - 20) / 40 * 20)
                confidence = "中"
            else:
                trend = MarketTrend.BEAR
                position_pct = 20
                confidence = "高"
            
            return {
                "date": date,
                "total_stocks": total,
                "above_ma20": above,
                "above_ma20_pct": above_pct,
                "below_ma20": below,
                "below_ma20_pct": below_pct,
                "trend": trend.value,
                "suggested_position_pct": position_pct,
                "confidence": confidence,
                "interpretation": self._get_interpretation(above_pct)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_interpretation(self, above_pct: float) -> str:
        """根据百分比给出解读"""
        if above_pct >= 80:
            return "🔥 全面沸腾，注意过热回调"
        elif above_pct >= 60:
            return "🟢 健康上升，可积极操作"
        elif above_pct >= 40:
            return "🟡 温和震荡，结构性机会"
        elif above_pct >= 20:
            return "🟡 弱势震荡，谨慎操作"
        elif above_pct >= 10:
            return "🔴 寒冷冬日，严控仓位"
        else:
            return "❄️  冰封时刻，接近大底"
    
    def get_position_rule_detailed(self, date: Optional[str] = None) -> Dict:
        """
        获取详细的仓位规则建议
        
        Returns:
            包含总仓位上限、单票上限、选股数量、风险提示
        """
        breadth = self.get_ma20_breadth(date)
        
        if "error" in breadth:
            return {
                "trend": "unknown",
                "total_position_pct": 30,
                "single_stock_max_pct": 15,
                "max_picks": 2,
                "risk_note": "数据不足，采用保守仓位",
                "breadth_raw": breadth
            }
        
        above_pct = breadth["above_ma20_pct"]
        
        if breadth["trend"] == MarketTrend.BULL.value:
            # 上升趋势：大胆进攻
            return {
                "trend": MarketTrend.BULL.value,
                "above_ma20_pct": above_pct,
                "total_position_pct": 80,
                "single_stock_max_pct": 20,
                "max_picks": 3,
                "risk_note": "环境安全，可积极操作",
                "core_principle": "趋势向上，重板块轻个股"
            }
        elif breadth["trend"] == MarketTrend.SHOCK.value:
            # 震荡市：中性偏谨慎
            position = breadth["suggested_position_pct"]
            return {
                "trend": MarketTrend.SHOCK.value,
                "above_ma20_pct": above_pct,
                "total_position_pct": position,
                "single_stock_max_pct": 15,
                "max_picks": 2,
                "risk_note": "震荡市，快进快出",
                "core_principle": "箱体思维，不追涨不杀跌"
            }
        else:
            # 下跌趋势：极度保守
            return {
                "trend": MarketTrend.BEAR.value,
                "above_ma20_pct": above_pct,
                "total_position_pct": 20,
                "single_stock_max_pct": 10,
                "max_picks": 1,
                "risk_note": "熊市，严控仓位，多看少动",
                "core_principle": "现金为王，只做超跌反弹"
            }
    
    def get_damper_status(self, date: Optional[str] = None) -> str:
        """
        获取阻尼器状态的人类可读字符串
        用于在报告中展示
        """
        data = self.get_position_rule_detailed(date)
        
        if "error" in data.get("breadth_raw", {}):
            return "大盘阻尼器：数据获取失败，使用保守模式"
        
        pct = data["above_ma20_pct"]
        trend = data["trend"]
        pos = data["total_position_pct"]
        
        lines = []
        lines.append(f"══════════════ 大盘阻尼器 ══════════════")
        lines.append(f"  全市场 MA20 均线广度: {pct}%")
        lines.append(f"  趋势判断: {trend}")
        lines.append(f"  建议仓位: {pos}%")
        lines.append(f"  单票上限: {data['single_stock_max_pct']}%")
        lines.append(f"  持股数量: 最多 {data['max_picks']} 只")
        lines.append(f"  {data['risk_note']}")
        lines.append(f"═══════════════════════════════════════")
        
        return "\n".join(lines)
