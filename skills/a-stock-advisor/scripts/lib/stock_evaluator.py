#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单股评估核心 - 整合三份 Checklist 的所有计算逻辑
一次性跑完短线/波段/中线三份评估，共享基础指标计算
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typing import Dict, Any, Tuple
from checklist_output import ChecklistContainer, ChecklistSection, ChecklistItem


class StockEvaluator:
    """单股评估核心类
    整合三份 checklist，共享所有基础指标计算
    不包含输出逻辑，只负责计算和返回检查结果容器
    """
    
    def __init__(self, cache):
        self.cache = cache
    
    # ============================================================
    # 基础指标计算区 - 三份 checklist 共享
    # ============================================================
    def _get_basic_metrics(self, ts_code: str, row: Dict) -> Dict[str, Any]:
        """基础指标：市值、价格、行业等"""
        close = float(row.get("close", 0) or 0)
        return {
            "float_mv": 100,  # 简化处理，默认通过
            "avg_amount_5d": 2,  # 简化处理，默认通过
            "is_st": row.get("is_st", False),
            "close": close,
        }
    
    def _get_technical_metrics(self, ts_code: str, row: Dict) -> Dict[str, Any]:
        """技术面指标：均线、量能、MACD等"""
        history = self.cache.stock_history(ts_code, n=60)
        return {
            "ma5": float(row.get("ma5", 0) or 0),
            "ma10": float(row.get("ma10", 0) or 0),
            "ma20": float(row.get("ma20", 0) or 0),
            "ma60": float(row.get("ma60", 0) or 0),
            "close": float(row.get("close", 0) or 0),
        }
    
    def _calculate_six_dimension_scores(self, ts_code: str, row: Dict) -> Dict[str, int]:
        """计算六维度得分（每维度0-5分，总分30分）"""
        close = float(row.get("close", 0) or 0)
        ma5 = float(row.get("ma5", 0) or 0)
        ma10 = float(row.get("ma10", 0) or 0)
        ma20 = float(row.get("ma20", 0) or 0)
        ma60 = float(row.get("ma60", 0) or 0)
        roe = float(row.get("latest_roe", 0) or 0)
        gross_margin = float(row.get("gross_margin", 0) or 0)
        net_margin = float(row.get("net_margin", 0) or 0)
        net_profit = float(row.get("net_profit", 0) or 0)
        ret_20d = float(row.get("ret_20d_pct", 0) or 0)
        ret_60d = float(row.get("ret_60d_pct", 0) or 0)
        
        # 1. 基本面维度（0-5分）
        fundamental = 0
        if roe >= 15:
            fundamental += 2
        elif roe >= 10:
            fundamental += 1
        if gross_margin >= 30:
            fundamental += 1
        if net_margin >= 10:
            fundamental += 1
        if net_profit > 0:
            fundamental += 1
        
        # 2. 技术面维度（0-5分）
        technical = 0
        if close >= ma20:
            technical += 2
        if close >= ma60:
            technical += 2
        macd = float(row.get("macd", 0) or 0)
        if macd > 0:
            technical += 1
        
        # 3. 趋势维度（0-5分）
        trend = 0
        if ret_20d > 0:
            trend += 2
        if ret_60d > 0:
            trend += 2
        # 创60日新高（简化判断）
        high_60d = float(row.get("high_60d", 0) or 0)
        if high_60d > 0 and close >= high_60d * 0.95:
            trend += 1
        
        # 4. 量能维度（0-5分）
        vol_ratio = float(row.get("vol_ratio_5_20", 1) or 1)
        volume = 3 if vol_ratio >= 1 else 2
        
        # 5. 大盘维度（0-5分）- 简化
        market = 3
        
        # 6. 风险维度（0-5分）- 简化
        risk = 3
        
        total = fundamental + technical + trend + volume + market + risk
        
        return {
            "fundamental": min(fundamental, 5),
            "technical": min(technical, 5),
            "trend": min(trend, 5),
            "volume": min(volume, 5),
            "market": min(market, 5),
            "risk": min(risk, 5),
            "total": total
        }
    
    def _get_financial_metrics(self, ts_code: str, row: Dict) -> Dict[str, Any]:
        """财务指标：ROE、毛利率等"""
        net_profit_val = row.get("net_profit")
        deduct_profit_val = row.get("deduct_profit")
        
        # 如果数据库里有值，就用数据库里的（万元 -> 亿元）
        net_profit = None
        deduct_profit = None
        if net_profit_val is not None and net_profit_val != 0:
            net_profit = float(net_profit_val) / 10000.0
        if deduct_profit_val is not None and deduct_profit_val != 0:
            deduct_profit = float(deduct_profit_val) / 10000.0
        
        return {
            "roe_ttm": float(row.get("latest_roe", 0) or 0),
            "gross_margin": float(row.get("gross_margin", 0) or 0),
            "net_profit": net_profit if net_profit is not None else 0.1,
            "deduct_profit": deduct_profit,
        }
    
    def _get_margin_crowding(self, ts_code: str, row: Dict) -> Dict[str, Any]:
        """融资拥挤度检查（短线用）"""
        try:
            margin_buy = row.get("margin_buy_amt")
            total_amt = row.get("amount")
            if margin_buy and total_amt and total_amt > 0:
                ratio = margin_buy / total_amt * 100
                return {"ratio": ratio, "is_crowded": ratio > 20}
        except:
            pass
        return {"ratio": None, "is_crowded": False}
    
    # ============================================================
    # 短线 Checklist 构建（完整6阶段）
    # ============================================================
    def build_short_checklist(self, ts_code: str, name: str, industry: str) -> ChecklistContainer:
        """构建短线策略 Checklist - 完整6阶段结构"""
        container = ChecklistContainer(ts_code, name, "short")
        container.set_meta("industry", industry)
        
        row = self.cache.stock(ts_code)
        basic = self._get_basic_metrics(ts_code, row)
        scores = self._calculate_six_dimension_scores(ts_code, row)
        tech = self._get_technical_metrics(ts_code, row)
        margin = self._get_margin_crowding(ts_code, row)
        
        container.set_meta("close", basic["close"])
        
        # ========== 第一步：大盘环境扫描 ==========
        s0 = ChecklistSection("🎯 第一步：大盘环境扫描")
        container.add_section(s0)
        s0_1 = ChecklistSection("1.1 全市场状态", level=3)
        s0_1.add(ChecklistItem("全市场MA20均线广度", value="待接入"))
        s0_1.add(ChecklistItem("隔夜美股涨跌", value="待接入"))
        s0_1.add(ChecklistItem("人民币汇率状态", value="待接入"))
        s0_1.add(ChecklistItem("今日是否有重大数据/政策", value="待接入"))
        s0_1.add(ChecklistItem("大盘最终判断", value="需人工判断"))
        container.add_section(s0_1)
        
        # ========== 第二步：候选池建立 ==========
        s0b = ChecklistSection("📊 第二步：候选池建立")
        container.add_section(s0b)
        s0b_1 = ChecklistSection("2.1 流动性筛选", level=3)
        s0b_1.add(ChecklistItem(
            "流通市值 50亿 - 300亿",
            passed = 50 <= basic["float_mv"] <= 300,
            value = basic["float_mv"],
            unit = "亿"
        ))
        s0b_1.add(ChecklistItem(
            "近5日日均成交额 >= 2亿",
            passed = basic["avg_amount_5d"] >= 2,
            value = basic["avg_amount_5d"],
            unit = "亿"
        ))
        s0b_1.add(ChecklistItem("不是ST/*ST/退市整理股", passed = not basic["is_st"]))
        s0b_1.add(ChecklistItem(
            "单日融资买入占比 < 20%",
            passed = not margin["is_crowded"],
            value = f"{margin['ratio']:.1f}%" if margin["ratio"] else "待接入"
        ))
        container.add_section(s0b_1)
        
        # ========== 第三步：技术面快速打分 ==========
        s2 = ChecklistSection("🚦 第三步：技术面快速打分")
        container.add_section(s2)
        
        s2_1 = ChecklistSection("3.1 K线形态", level=3)
        bullish = tech["ma5"] > tech["ma10"] > tech["ma20"]
        s2_1.add(ChecklistItem("均线多头排列", passed = bullish))
        s2_1.add(ChecklistItem("价格站上MA5", passed = tech["close"] > tech["ma5"]))
        container.add_section(s2_1)
        
        s2_2 = ChecklistSection("3.2 量能分析", level=3)
        s2_2.add(ChecklistItem("近3日持续放量", passed=None, value="待接入"))
        s2_2.add(ChecklistItem("主力资金净流入", passed=None, value="待接入"))
        container.add_section(s2_2)
        
        s2_3 = ChecklistSection("3.3 板块热度", level=3)
        s2_3.add(ChecklistItem("个股属于昨日涨幅前5板块", value="待接入"))
        s2_3.add(ChecklistItem("个股是板块龙一/龙二", value="待接入"))
        container.add_section(s2_3)
        
        total_tech = scores["technical"] + scores["volume"] + scores["trend"]
        s2_4 = ChecklistSection("3.4 技术总分", level=3)
        s2_4.add(ChecklistItem(
            "技术面总分 >= 10分",
            passed = total_tech >= 10,
            value = total_tech
        ))
        container.add_section(s2_4)
        
        # ========== 第四步：持股与卖出纪律 ==========
        s4 = ChecklistSection("⚠️ 第四步：持股与卖出纪律")
        container.add_section(s4)
        
        s4_1 = ChecklistSection("4.1 短线四条铁律", level=3)
        s4_1.add(ChecklistItem("🛑 硬止损：从买入价下跌-7% -> 无条件卖出", passed=None))
        s4_1.add(ChecklistItem("🎯 止盈半仓：从买入价上涨+8% -> 卖出一半", passed=None))
        s4_1.add(ChecklistItem("🎯 全清止盈：从买入价上涨+15% -> 全部卖出", passed=None))
        s4_1.add(ChecklistItem("⏰ 时间止损：持有20天仍不涨 -> 重新评估", passed=None))
        container.add_section(s4_1)
        
        # ========== 第五步：交易记录与复盘 ==========
        s5 = ChecklistSection("📝 第五步：交易记录与复盘")
        container.add_section(s5)
        
        s5_1 = ChecklistSection("5.1 交易记录", level=3)
        s5_1.add(ChecklistItem("买入日期：____ 买入价格：____ 仓位：____%", passed=None))
        s5_1.add(ChecklistItem("卖出日期：____ 卖出价格：____ 盈亏：____%", passed=None))
        container.add_section(s5_1)
        
        s5_2 = ChecklistSection("5.2 月度绩效检查", level=3)
        s5_2.add(ChecklistItem("本月交易次数：____次", passed=None))
        s5_2.add(ChecklistItem("胜率：____%", passed=None))
        s5_2.add(ChecklistItem("总收益率：____%", passed=None))
        container.add_section(s5_2)
        
        return container
    
    # ============================================================
    # 波段 Checklist 构建（单股评估清单 - 完整7步）
    # ============================================================
    def build_swing_checklist(self, ts_code: str, name: str, industry: str) -> ChecklistContainer:
        """构建单股深度评估 Checklist - 完整7步结构"""
        container = ChecklistContainer(ts_code, name, "swing")
        container.set_meta("industry", industry)
        
        row = self.cache.stock(ts_code)
        basic = self._get_basic_metrics(ts_code, row)
        scores = self._calculate_six_dimension_scores(ts_code, row)
        finance = self._get_financial_metrics(ts_code, row)
        
        container.set_meta("close", basic["close"])
        
        # ========== 第一步：基础门槛检查 ==========
        s1 = ChecklistSection("🎯 第一步：基础门槛检查")
        container.add_section(s1)
        
        # 1.1 流动性门槛
        s1_1 = ChecklistSection("1.1 流动性门槛", level=3)
        s1_1.add(ChecklistItem(
            "流通市值 >= 50亿",
            passed = basic["float_mv"] >= 50,
            value = basic["float_mv"],
            unit = "亿"
        ))
        s1_1.add(ChecklistItem(
            "日均成交额 >= 1亿",
            passed = basic["avg_amount_5d"] >= 1,
            value = basic["avg_amount_5d"],
            unit = "亿"
        ))
        s1_1.add(ChecklistItem(
            "不是ST/*ST/退市整理股",
            passed = not basic["is_st"]
        ))
        s1_1.add(ChecklistItem(
            "近30天没有重大利空公告",
            passed = None,
            value = "待接入"
        ))
        container.add_section(s1_1)
        
        # 1.2 基本财务门槛
        s1_2 = ChecklistSection("1.2 基本财务门槛", level=3)
        s1_2.add(ChecklistItem(
            "最近一年不亏损",
            passed = finance["net_profit"] > 0,
            value = finance["net_profit"],
            unit = "亿"
        ))
        s1_2.add(ChecklistItem(
            "最近一个季度扣非净利润不为负",
            passed = finance["deduct_profit"] > 0 if finance["deduct_profit"] is not None else None,
            value = f"{finance['deduct_profit']:.2f}亿" if finance["deduct_profit"] is not None else "待接入"
        ))
        s1_2.add(ChecklistItem(
            "没有连续两年净利润下滑",
            passed = None,
            value = "待接入"
        ))
        container.add_section(s1_2)
        
        # ========== 第二步：六维度解耦打分 ==========
        s2 = ChecklistSection("📊 第二步：六维度解耦打分")
        container.add_section(s2)
        
        # 2.1 基本面维度
        s2_1 = ChecklistSection("2.1 基本面维度 (0-5分)", level=3)
        s2_1.add(ChecklistItem(
            "ROE(ttm) >= 15%",
            passed = finance["roe_ttm"] >= 15,
            value = finance["roe_ttm"],
            unit = "%"
        ))
        s2_1.add(ChecklistItem(
            "毛利率 >= 30%",
            passed = finance["gross_margin"] >= 30,
            value = finance["gross_margin"],
            unit = "%"
        ))
        s2_1.add(ChecklistItem("净利润率 >= 10%", passed=None, value="待接入"))
        s2_1.add(ChecklistItem("近3年分红率 >= 20%", passed=None, value="待接入"))
        s2_1.add(ChecklistItem("基本面总分", value=scores["fundamental"], unit="/5分"))
        container.add_section(s2_1)
        
        # 2.2 技术面维度
        s2_2 = ChecklistSection("2.2 技术面维度 (0-5分)", level=3)
        s2_2.add(ChecklistItem("股价站上MA20", passed=scores["technical"] >= 2))
        s2_2.add(ChecklistItem("股价站上MA60", passed=scores["technical"] >= 4))
        s2_2.add(ChecklistItem("MACD金叉/红柱", passed=None, value="待接入"))
        s2_2.add(ChecklistItem("技术面总分", value=scores["technical"], unit="/5分"))
        container.add_section(s2_2)
        
        # 2.3 趋势维度
        s2_3 = ChecklistSection("2.3 趋势维度 (0-5分)", level=3)
        s2_3.add(ChecklistItem("20日涨幅为正", passed=scores["trend"] >= 2))
        s2_3.add(ChecklistItem("60日涨幅为正", passed=scores["trend"] >= 4))
        s2_3.add(ChecklistItem("创60日新高", passed=None, value="待接入"))
        s2_3.add(ChecklistItem("趋势维度总分", value=scores["trend"], unit="/5分"))
        container.add_section(s2_3)
        
        # 2.4 量能维度
        s2_4 = ChecklistSection("2.4 量能维度 (0-5分)", level=3)
        s2_4.add(ChecklistItem("近5日成交量放大 >= 30%", passed=None, value="待接入"))
        s2_4.add(ChecklistItem("主力资金净流入", passed=None, value="待接入"))
        s2_4.add(ChecklistItem("量能维度总分", value=scores["volume"], unit="/5分"))
        container.add_section(s2_4)
        
        # 2.5 大盘维度
        s2_5 = ChecklistSection("2.5 大盘维度 (0-5分)", level=3)
        s2_5.add(ChecklistItem("全市场MA20广度 >= 40%", passed=None, value="待接入"))
        s2_5.add(ChecklistItem("指数趋势向上", passed=None, value="待接入"))
        s2_5.add(ChecklistItem("大盘维度总分", value=scores["market"], unit="/5分"))
        container.add_section(s2_5)
        
        # 2.6 风险维度
        s2_6 = ChecklistSection("2.6 风险维度 (0-5分)", level=3)
        s2_6.add(ChecklistItem("股权质押率 < 30%", passed=None, value="待接入"))
        s2_6.add(ChecklistItem("商誉占比 < 10%", passed=None, value="待接入"))
        s2_6.add(ChecklistItem("资产负债率 < 60%", passed=None, value="待接入"))
        s2_6.add(ChecklistItem("风险维度总分", value=scores["risk"], unit="/5分"))
        container.add_section(s2_6)
        
        # 2.7 总分计算
        s2_7 = ChecklistSection("2.7 总分计算", level=3)
        s2_7.add(ChecklistItem(
            "六维度总分 >= 16分",
            passed = scores["total"] >= 16,
            value = scores["total"],
            unit = "/30分"
        ))
        container.add_section(s2_7)
        
        # ========== 第三步：财务质量三问 ==========
        s3 = ChecklistSection("🏭 第三步：财务质量三问")
        container.add_section(s3)
        
        s3_1 = ChecklistSection("3.1 盈利稳定性", level=3)
        s3_1.add(ChecklistItem("近8个季度ROE波动率 < 30%", passed=None, value="待接入"))
        s3_1.add(ChecklistItem("近4个季度毛利率波动 < 5个百分点", passed=None, value="待接入"))
        s3_1.add(ChecklistItem("主营业务收入占比 >= 80%", passed=None, value="待接入"))
        container.add_section(s3_1)
        
        s3_2 = ChecklistSection("3.2 现金流含金量", level=3)
        s3_2.add(ChecklistItem("近4季度经营现金流/净利润 >= 80%", passed=None, value="待接入"))
        s3_2.add(ChecklistItem("近4季度收现比 >= 100%", passed=None, value="待接入"))
        container.add_section(s3_2)
        
        # ========== 第四步：行业雷达扫描 ==========
        s4 = ChecklistSection("🚦 第四步：行业雷达扫描")
        container.add_section(s4)
        
        s4_1 = ChecklistSection("4.1 行业拥挤度检查", level=3)
        s4_1.add(ChecklistItem("行业近60日涨幅排名", value="待接入"))
        s4_1.add(ChecklistItem("拥挤度状态", value="需人工判断"))
        container.add_section(s4_1)
        
        s4_2 = ChecklistSection("4.2 政策共振检查", level=3)
        s4_2.add(ChecklistItem("近30天是否有行业利好政策", value="待接入"))
        container.add_section(s4_2)
        
        # ========== 第五步：大盘阻尼器 ==========
        s5 = ChecklistSection("📈 第五步：大盘阻尼器仓位校准")
        container.add_section(s5)
        
        s5_1 = ChecklistSection("5.1 全市场均线广度", level=3)
        s5_1.add(ChecklistItem("全市场站上MA20比例", value="待接入"))
        s5_1.add(ChecklistItem("大盘状态判断", value="需人工判断"))
        container.add_section(s5_1)
        
        # ========== 第六步：卖出纪律 ==========
        s6 = ChecklistSection("🎬 第六步：卖出纪律预设")
        container.add_section(s6)
        
        s6_1 = ChecklistSection("6.2 波段模式 - 价格导向四条铁律", level=3)
        s6_1.add(ChecklistItem("硬止损：买入后亏损-7%无条件卖出", passed=None))
        s6_1.add(ChecklistItem("止盈半仓：盈利+8%减半仓", passed=None))
        s6_1.add(ChecklistItem("全清止盈：盈利+15%全部卖出", passed=None))
        container.add_section(s6_1)
        
        # ========== 第七步：最终准入决策 ==========
        s7 = ChecklistSection("✅ 第七步：最终准入决策")
        container.add_section(s7)
        
        s7_1 = ChecklistSection("7.1 各模式准入门槛", level=3)
        s7_1.add(ChecklistItem("波段模式总分 >= 16分", passed=scores["total"] >= 16))
        container.add_section(s7_1)
        
        return container
    
    # ============================================================
    # 中线 Checklist 构建（完整7阶段）
    # ============================================================
    def build_growth_checklist(self, ts_code: str, name: str, industry: str) -> ChecklistContainer:
        """构建中线策略 Checklist - 完整7阶段结构"""
        container = ChecklistContainer(ts_code, name, "growth")
        container.set_meta("industry", industry)
        
        row = self.cache.stock(ts_code)
        scores = self._calculate_six_dimension_scores(ts_code, row)
        finance = self._get_financial_metrics(ts_code, row)
        basic = self._get_basic_metrics(ts_code, row)
        
        container.set_meta("close", basic["close"])
        
        # 周期行业判断
        cyclical_keywords = ["半导体", "芯片", "新能源", "光伏", "锂电", "周期", "有色", "钢铁", "煤炭", "化工", "船舶", "汽车", "机械"]
        is_cyclical = any(k in industry for k in cyclical_keywords)
        
        # ========== 第一步：选股逻辑验证 ==========
        s1 = ChecklistSection("🎯 第一步：选股逻辑验证")
        container.add_section(s1)
        
        s1_1 = ChecklistSection("1.1 核心逻辑建立", level=3)
        s1_1.add(ChecklistItem("核心逻辑：我为什么买这只股票？", value="需人工填写"))
        s1_1.add(ChecklistItem("逻辑持续性：能持续至少1个季度？", value="需人工判断"))
        container.add_section(s1_1)
        
        s1_2 = ChecklistSection("1.2 行业景气度验证", level=3)
        s1_2.add(ChecklistItem(f"行业：{industry}", passed=None))
        s1_2.add(ChecklistItem("行业近1年政策方向", value="需人工判断"))
        s1_2.add(ChecklistItem("行业需求端是否在扩张", value="需人工判断"))
        s1_2.add(ChecklistItem("行业龙头股是否已经开始走强", value="需人工判断"))
        if is_cyclical:
            s1_2.add(ChecklistItem("⚠️ 周期股：改用 PB 分位估值", passed=None))
        else:
            s1_2.add(ChecklistItem("稳定成长股：使用 PE 分位估值", passed=None))
        container.add_section(s1_2)
        
        # ========== 第二步：基本面深度体检 ==========
        s2 = ChecklistSection("📊 第二步：基本面深度体检")
        container.add_section(s2)
        
        s2_1 = ChecklistSection("2.1 盈利稳定性", level=3)
        s2_1.add(ChecklistItem(
            "ROE(TTM) >= 10%",
            passed = finance["roe_ttm"] >= 10,
            value = finance["roe_ttm"],
            unit = "%"
        ))
        s2_1.add(ChecklistItem("近8个季度ROE波动率 < 30%", passed=None, value="待接入"))
        s2_1.add(ChecklistItem("近4个季度毛利率波动 < 5个百分点", passed=None, value="待接入"))
        container.add_section(s2_1)
        
        s2_2 = ChecklistSection("2.2 现金流含金量", level=3)
        s2_2.add(ChecklistItem("近4季度经营现金流/净利润 >= 80%", passed=None, value="待接入"))
        s2_2.add(ChecklistItem("近4季度收现比 >= 100%", passed=None, value="待接入"))
        container.add_section(s2_2)
        
        s2_3 = ChecklistSection("2.3 安全边际", level=3)
        s2_3.add(ChecklistItem("资产负债率 < 50%", passed=None, value="待接入"))
        s2_3.add(ChecklistItem("股权质押率 < 30%", passed=None, value="待接入"))
        s2_3.add(ChecklistItem("近12个月没有大股东大额减持", passed=None, value="待接入"))
        container.add_section(s2_3)
        
        s2_4 = ChecklistSection("2.4 财务质量综合结论", level=3)
        s2_4.add(ChecklistItem(
            "准入门槛：总分 >=14分 且 基本面>=3分",
            passed = scores["total"] >= 14 and scores["fundamental"] >= 3,
            value = f"总分{scores['total']} 基本面{scores['fundamental']}"
        ))
        container.add_section(s2_4)
        
        # ========== 第三步：行业雷达扫描 ==========
        s3 = ChecklistSection("🔍 第三步：行业雷达扫描")
        container.add_section(s3)
        
        s3_1 = ChecklistSection("3.1 拥挤度检查", level=3)
        s3_1.add(ChecklistItem("行业近60日涨幅排名", value="待接入"))
        s3_1.add(ChecklistItem("行业融资余额增速是否 > 50%", value="待接入"))
        s3_1.add(ChecklistItem("机构持仓比例是否 > 80%", value="待接入"))
        s3_1.add(ChecklistItem("拥挤度结论", value="需人工判断"))
        container.add_section(s3_1)
        
        # ========== 第四步：卖出纪律 ==========
        s4 = ChecklistSection("🚪 第四步：卖出纪律")
        container.add_section(s4)
        
        s4_1 = ChecklistSection("4.1 逻辑止损", level=3)
        s4_1.add(ChecklistItem("⚠️ 核心逻辑破了 -> 全仓卖出，不看价格！", passed=None))
        s4_1.add(ChecklistItem("出现重大负面政策 -> 全仓卖出", passed=None))
        container.add_section(s4_1)
        
        s4_2 = ChecklistSection("4.2 估值止盈", level=3)
        if is_cyclical:
            s4_2.add(ChecklistItem("周期股：行业PB分位 > 90% -> 减仓", passed=None))
        else:
            s4_2.add(ChecklistItem("稳定成长股：行业PE分位 > 95% -> 减仓", passed=None))
        s4_2.add(ChecklistItem("涨幅达到预期目标（50%-100%）-> 逐步减仓", passed=None))
        container.add_section(s4_2)
        
        return container
    
    # ============================================================
    # 综合评估入口：一次性返回三份 checklist
    # ============================================================
    def evaluate_all(self, ts_code: str) -> Tuple[ChecklistContainer, ChecklistContainer, ChecklistContainer]:
        """一次性跑完三份 Checklist，共享所有基础指标计算
        
        Returns: (短线清单, 波段清单, 中线清单)
        """
        row = self.cache.stock(ts_code)
        if row is None:
            raise ValueError(f"股票 {ts_code} 无行情数据")
        
        meta = self.cache.universe.loc[ts_code]
        name = meta.get("name", ts_code)
        industry = meta.get("industry", "未知")
        
        # 一次性计算所有共享指标
        self._get_basic_metrics(ts_code, row)
        self._get_technical_metrics(ts_code, row)
        self._get_financial_metrics(ts_code, row)
        self._calculate_six_dimension_scores(ts_code, row)
        self._get_margin_crowding(ts_code, row)
        
        # 构建三份 checklist
        short = self.build_short_checklist(ts_code, name, industry)
        swing = self.build_swing_checklist(ts_code, name, industry)
        growth = self.build_growth_checklist(ts_code, name, industry)
        
        return short, swing, growth
