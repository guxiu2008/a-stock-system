#!/usr/bin/env python3
"""
v2 七步法选股策略 - 实盘版 + 行业雷达升级
支持三种模式：
- short:  2~4 周，目标 +8%，偏短线波段（技术面驱动 + 拥挤度过滤）
- swing:  1~3 个月，目标 +15~25%，偏中期波段（技术+行业轮动 + 拥挤度过滤）
- growth: 3~6 个月，目标 +30~50%，偏中期成长（基本面驱动 + 政策共振逆向布局）

核心升级：行业雷达
1. 行业拥挤度检测 - 防止散户高位接盘
2. 政策共振检测 - 寻找中线超跌 + 政策吹风的逆向布局机会
"""
import pandas as pd
import numpy as np
import os
try:
    from lib.industry_radar import IndustryRadar
except ImportError:
    IndustryRadar = None
try:
    from lib.market_damper import MarketDamper, MarketTrend
except ImportError:
    MarketDamper = None
    MarketTrend = None


OPTIMAL_PARAMS = {
    "mode": "short",
    "industry_rank_range": (3, 12),
    "max_industry_3d_pct": 15.0,
    "min_buy_score": 4,       # 短线模式：技术面硬门槛，趋势和量能优先
    "min_roe": 0.0,            # 短线模式：基本面放宽，只需 ROE>0
    "require_dividend": True,  # 短线仍要求分红（排除纯题材股）
    "mid_pct_lo": 0.3,
    "mid_pct_hi": 0.7,
}


SWING_PARAMS = {
    "mode": "swing",
    "industry_rank_range": (3, 15),
    "min_buy_score": 3,       # 波段模式：平衡标准
    "min_roe": 5.0,            # 波段模式：中等基本面要求
    "require_dividend": True,
    "mid_pct_lo": 0.25,
    "mid_pct_hi": 0.75,
}


GROWTH_PARAMS = {
    "mode": "growth",
    "industry_rank_range": (1, 20),
    "min_buy_score": 2,       # 成长模式：技术面放宽，允许左侧布局
    "min_roe": 10.0,           # 成长模式：基本面硬门槛
    "require_dividend": True,  # 成长模式也要求分红（排除烧钱模式）
    "mid_pct_lo": 0.1,
    "mid_pct_hi": 0.9,
    "exclude_industries": ["电力", "火力发电", "水务", "燃气", "供气供热", "银行", "保险", "地产", "建筑", "钢铁", "煤炭", "石油", "路桥", "港口", "高速公路"],
}


def _sentiment_to_label(sentiment: int) -> str:
    if sentiment >= 90:
        return "🔥 极度亢奋"
    elif sentiment >= 75:
        return "🟢 情绪乐观"
    elif sentiment >= 60:
        return "🟡 情绪偏多"
    elif sentiment >= 40:
        return "⚪ 情绪中性"
    elif sentiment >= 25:
        return "🟡 情绪偏空"
    elif sentiment >= 10:
        return "🔴 情绪悲观"
    else:
        return "❄️ 极度恐慌"


def get_position_rule(trend: str, rsi_signal: str = "正常", sentiment: int = 50, extreme_move: bool = False) -> dict:
    base_rules = {
        "上升趋势": {"max_total": 0.8, "max_single": 0.20, "max_picks": 3},
        "震荡市":   {"max_total": 0.5, "max_single": 0.15, "max_picks": 2},
        "下跌趋势": {"max_total": 0.2, "max_single": 0.10, "max_picks": 1},
        "unknown":  {"max_total": 0.3, "max_single": 0.15, "max_picks": 1},
    }
    rule = base_rules.get(trend, base_rules["unknown"]).copy()
    
    # RSI超买时降低仓位和推荐数量
    if rsi_signal == "极度超买":
        rule["max_total"] *= 0.6
        rule["max_single"] *= 0.7
        rule["max_picks"] = max(1, rule["max_picks"] - 1)
    elif rsi_signal == "超买":
        rule["max_total"] *= 0.8
        rule["max_picks"] = max(1, rule["max_picks"] - 1)
    # RSI超卖时可以适当增加仓位（左侧布局）
    elif rsi_signal == "极度超卖":
        rule["max_total"] = min(0.9, rule["max_total"] * 1.2)
    elif rsi_signal == "超卖":
        rule["max_total"] = min(0.85, rule["max_total"] * 1.1)
    
    # 极端行情（单日涨跌≥3%）时进一步保守
    if extreme_move:
        rule["max_total"] *= 0.7
        rule["max_picks"] = max(1, rule["max_picks"] - 1)
    
    return rule


class StockSelector:
    def __init__(self, cache, mode: str = "growth", **params):
        self.cache = cache
        if mode == "growth":
            base = GROWTH_PARAMS
        elif mode == "swing":
            base = SWING_PARAMS
        else:
            base = OPTIMAL_PARAMS
        p = {**base, **params}
        self.mode = p["mode"]
        self.industry_rank_range = p["industry_rank_range"]
        self.max_industry_3d_pct = p.get("max_industry_3d_pct", 15.0)
        self.min_buy_score = p["min_buy_score"]
        self.min_roe = p["min_roe"]
        self.require_dividend = p["require_dividend"]
        self.mid_pct_lo = p["mid_pct_lo"]
        self.mid_pct_hi = p["mid_pct_hi"]
        self.exclude_industries = p.get("exclude_industries", [])
        
        # 初始化行业雷达（升级版板块筛选）
        self.radar = None
        if IndustryRadar is not None:
            db_path = os.environ.get("STOCK_DB_PATH", "stock_data.db")
            if os.path.exists(db_path):
                self.radar = IndustryRadar(db_path)
        
        # 初始化大盘阻尼器（升级版仓位控制 - 用全市场均线广度）
        self.damper = None
        if MarketDamper is not None:
            db_path = os.environ.get("STOCK_DB_PATH", "stock_data.db")
            if os.path.exists(db_path):
                self.damper = MarketDamper(db_path)

    def select(self, date: str = None, candidate_limit: int = 5) -> dict:
        date = date or self.cache.latest_date
        trend = self.cache.trend(date)
        rsi_signal = self.cache.rsi_signal(date)
        sentiment = self.cache.sentiment(date)
        extreme_move = self.cache.is_extreme_move(date)
        index_rsi = self.cache.index_rsi(date)
        index_pct = self.cache.index_pct(date)
        trend_change = self.cache.trend_change(date)
        consecutive_up = self.cache.consecutive_up_days(date)
        consecutive_down = self.cache.consecutive_down_days(date)
        is_macd_red = self.cache.is_macd_red(date)
        is_macd_gold_cross = self.cache.is_macd_gold_cross(date)
        forecast = self.cache.get_market_forecast(date)
        
        # ========== 大盘阻尼器：升级版仓位控制（核心升级）==========
        damper_result = None
        if self.damper is not None:
            damper_result = self.damper.get_position_rule_detailed(date)
            if "error" not in damper_result:
                # 阻尼器数据有效，使用阻尼器仓位
                position_rule = {
                    "max_total": damper_result["total_position_pct"],
                    "max_single": damper_result["single_stock_max_pct"],
                    "max_picks": damper_result["max_picks"],
                    "source": "大盘阻尼器（全市场均线广度）",
                    "above_ma20_pct": damper_result.get("above_ma20_pct"),
                }
                damper_note = f"[大盘阻尼器] 全市场{damper_result.get('above_ma20_pct')}%股票站上MA20，" \
                             f"建议仓位{damper_result['total_position_pct']}%"
            else:
                # 降级方案：使用原有的简单趋势判断
                position_rule = get_position_rule(trend, rsi_signal, sentiment, extreme_move)
                damper_note = "[大盘阻尼器] 数据获取失败，降级使用传统趋势判断"
        else:
            # 阻尼器不可用，回退到传统方法
            position_rule = get_position_rule(trend, rsi_signal, sentiment, extreme_move)
            damper_note = None
        
        result = {
            "date": date,
            "mode": self.mode,
            "trend": trend,
            "trend_change": trend_change,
            "rsi_signal": rsi_signal,
            "sentiment": sentiment,
            "sentiment_label": _sentiment_to_label(sentiment),
            "index_rsi": index_rsi,
            "index_pct": index_pct,
            "extreme_move": extreme_move,
            "consecutive_up": consecutive_up,
            "consecutive_down": consecutive_down,
            "is_macd_red": is_macd_red,
            "is_macd_gold_cross": is_macd_gold_cross,
            "forecast": forecast,
            "damper_enabled": self.damper is not None,
            "damper_result": damper_result,
            "position_rule": position_rule,
            "top_industries": [],
            "picks": [],
            "notes": [],
        }
        
        # 添加阻尼器日志
        if damper_note:
            result["notes"].append(damper_note)

        if trend == "unknown":
            result["notes"].append("大盘趋势数据缺失，无法判断")
            return result

        df = self.cache.daily(date)
        if df.empty:
            result["notes"].append(f"日期 {date} 无数据")
            return result

        if self.mode == "short":
            return self._select_short(df, result, date, candidate_limit)
        elif self.mode == "growth":
            return self._select_growth(df, result, date, candidate_limit)
        return self._select_swing(df, result, date, candidate_limit)

    def _select_short(self, df: pd.DataFrame, result: dict, date: str, candidate_limit: int = 5) -> dict:
        df = df.dropna(subset=["cum_3d_pct"])
        
        # ========== 行业雷达升级：拥挤度过滤 ==========
        if self.radar is not None:
            # 使用行业雷达筛选：动量排名 + 拥挤度过滤
            target_inds = self.radar.select_industries_short(
                df, 
                rank_range=self.industry_rank_range,
                max_3d_pct=self.max_industry_3d_pct,
                crowding_threshold=0.3  # 拥挤度阈值：超过30%波动视为过热
            )
            
            # 记录拥挤度过滤效果
            if target_inds:
                crowding = self.radar.get_industry_crowding_score(df)
                filtered_count = len([ind for ind in crowding if crowding[ind] > 0.3])
                if filtered_count > 0:
                    result["notes"].append(f"[短线雷达] 拥挤度过滤：排除 {filtered_count} 个过热行业，保留 {len(target_inds)} 个")
            else:
                result["notes"].append("[短线雷达] 拥挤度过滤后无有效行业，降级为原始筛选")
                # 降级方案
                ind_perf = df.groupby("industry")["cum_3d_pct"].agg(["mean", "count"]).reset_index()
                ind_perf = ind_perf[ind_perf["count"] >= 5]
                ind_perf = ind_perf[ind_perf["mean"] <= self.max_industry_3d_pct]
                ind_perf = ind_perf.sort_values("mean", ascending=False).reset_index(drop=True)
                target_inds = self._target_industries(ind_perf)
        else:
            # 无雷达时的原始筛选
            ind_perf = df.groupby("industry")["cum_3d_pct"].agg(["mean", "count"]).reset_index()
            ind_perf = ind_perf[ind_perf["count"] >= 5]
            ind_perf = ind_perf[ind_perf["mean"] <= self.max_industry_3d_pct]
            ind_perf = ind_perf.sort_values("mean", ascending=False).reset_index(drop=True)
            target_inds = self._target_industries(ind_perf)
        
        # 保存TOP行业列表供展示
        ind_display = df.groupby("industry")["cum_3d_pct"].agg(["mean", "count"]).reset_index()
        ind_display = ind_display[ind_display["count"] >= 5].sort_values("mean", ascending=False)
        result["top_industries"] = [
            {"industry": r["industry"], "score": round(r["mean"], 2), "stock_count": int(r["count"])}
            for _, r in ind_display.head(15).iterrows()
        ]
        
        if not target_inds:
            result["notes"].append("无有效行业（可能是大盘极弱）")
            return result
            
        sub = self._base_filter(df[df["industry"].isin(target_inds)].copy(), date)
        sub = sub[sub["cum_3d_pct"] > 0]
        sub = sub[sub["close"] > sub["ma20"]]
        return self._finish_selection(sub, result, date, metric="cum_3d_pct", candidate_limit=candidate_limit)

    def _select_swing(self, df: pd.DataFrame, result: dict, date: str, candidate_limit: int = 5) -> dict:
        df = df.dropna(subset=["ret_20d_pct", "ret_60d_pct", "ma60"])
        df = df.copy()
        df["industry_strength"] = df["ret_20d_pct"] * 0.6 + df["ret_60d_pct"] * 0.4
        
        # ========== 行业雷达升级：拥挤度过滤 ==========
        if self.radar is not None:
            # 使用行业雷达筛选：中期强度排名 + 拥挤度过滤
            target_inds = self.radar.select_industries_swing(
                df, 
                rank_range=self.industry_rank_range,
                crowding_threshold=0.25  # 波段模式更保守，拥挤度阈值更低
            )
            
            if target_inds:
                crowding = self.radar.get_industry_crowding_score(df)
                filtered_count = len([ind for ind in crowding if crowding[ind] > 0.25])
                if filtered_count > 0:
                    result["notes"].append(f"[波段雷达] 拥挤度过滤：排除 {filtered_count} 个过热行业，保留 {len(target_inds)} 个")
            else:
                result["notes"].append("[波段雷达] 拥挤度过滤后无有效行业，降级为原始筛选")
                # 降级方案
                ind_perf = df.groupby("industry").agg(
                    mean=("industry_strength", "mean"),
                    count=("industry", "count"),
                ).reset_index()
                ind_perf = ind_perf[(ind_perf["count"] >= 5)]
                ind_perf = ind_perf.sort_values("mean", ascending=False).reset_index(drop=True)
                target_inds = self._target_industries(ind_perf)
        else:
            # 无雷达时的原始筛选
            ind_perf = df.groupby("industry").agg(
                mean=("industry_strength", "mean"),
                count=("industry", "count"),
            ).reset_index()
            ind_perf = ind_perf[(ind_perf["count"] >= 5)]
            ind_perf = ind_perf.sort_values("mean", ascending=False).reset_index(drop=True)
            target_inds = self._target_industries(ind_perf)
        
        # 保存TOP行业列表供展示
        ind_display = df.groupby("industry").agg(
            mean=("industry_strength", "mean"),
            ret20=("ret_20d_pct", "mean"),
            ret60=("ret_60d_pct", "mean"),
            count=("industry", "count"),
        ).reset_index()
        ind_display = ind_display[(ind_display["count"] >= 5)].sort_values("mean", ascending=False)
        result["top_industries"] = [
            {"industry": r["industry"], "score": round(r["mean"], 2), "ret20": round(r["ret20"], 2), "ret60": round(r["ret60"], 2), "stock_count": int(r["count"])}
            for _, r in ind_display.head(15).iterrows()
        ]
        
        if not target_inds:
            result["notes"].append("无有效中期趋势行业")
            return result
            
        sub = self._base_filter(df[df["industry"].isin(target_inds)].copy(), date)
        sub = sub[(sub["ret_20d_pct"] > -5) & (sub["ret_20d_pct"] < 35)]
        sub = sub[(sub["ret_60d_pct"] > -15) & (sub["ret_60d_pct"] < 80)]
        sub = sub[sub["close"] > sub["ma60"]]
        sub = sub[sub["vol_ratio_5_20"].fillna(1).between(0.7, 3.5)]
        sub["swing_score"] = (
            sub["buy_score"] * 8
            + sub["ret_20d_pct"].clip(-10, 30) * 0.5
            + sub["ret_60d_pct"].clip(-20, 60) * 0.3
            + sub["latest_roe"].fillna(0).clip(-5, 25) * 0.6
            - sub["dist_60d_high_pct"].abs().clip(0, 20) * 0.05
        )
        return self._finish_selection(sub, result, date, metric="swing_score", candidate_limit=candidate_limit)

    def _select_growth(self, df: pd.DataFrame, result: dict, date: str, candidate_limit: int = 5) -> dict:
        """
        中期成长策略 - 行业雷达升级版
        核心逻辑：寻找"中线超跌 + 政策吹风"的行业（真正的逆向布局）
        目标：30~50%收益
        """
        df = df.dropna(subset=["latest_roe", "gross_margin", "ma60"])
        
        df["growth_score"] = (
            df["latest_roe"].clip(0, 40) * 2.5
            + df["gross_margin"].fillna(0).clip(0, 80) * 0.6
            + df["net_margin"].fillna(0).clip(0, 50) * 0.4
        )

        # ========== 行业雷达升级：中线超跌 + 政策共振 ==========
        target_inds = []
        policy_resonance_found = False
        
        if self.radar is not None:
            # 尝试逆向布局策略：中线超跌 + 近7日政策吹风
            target_inds = self.radar.select_industries_growth(
                df,
                lookback_days=7,       # 近7日政策
                top_oversold=15,       # 60日跌幅前15行业
                top_policy=8           # 政策密度前8行业
            )
            
            if target_inds:
                policy_resonance_found = True
                # 获取政策共振详情
                policy_scores = self.radar.get_policy_resonance(lookback_days=7)
                oversold_inds = self.radar.get_oversold_industries(df, top_n=15)
                
                result["notes"].append(f"[成长雷达] 政策共振逆向布局：锁定 {len(target_inds)} 个行业")
                for ind in target_inds:
                    policy_count = policy_scores.get(ind, 0)
                    result["notes"].append(f"  - {ind}：60日超跌排名前15，近7日政策提及 {policy_count} 次")
            else:
                result["notes"].append("[成长雷达] 未找到政策共振行业，降级为基本面排名筛选")
        
        # 降级方案：按基本面排名筛选
        if not target_inds:
            ind_perf = df.groupby("industry").agg(
                mean_growth=("growth_score", "mean"),
                mean_roe=("latest_roe", "mean"),
                count=("industry", "count"),
                high_roe_cnt=("latest_roe", lambda x: (x >= self.min_roe).sum()),
            ).reset_index()
            ind_perf = ind_perf[ind_perf["count"] >= 5]
            ind_perf = ind_perf.sort_values("high_roe_cnt", ascending=False).reset_index(drop=True)
            target_inds = ind_perf.head(15)["industry"].tolist()
        
        # 保存TOP行业列表供展示
        ind_display = df.groupby("industry").agg(
            mean_growth=("growth_score", "mean"),
            mean_roe=("latest_roe", "mean"),
            ret_60d=("ret_60d_pct", "mean"),
            count=("industry", "count"),
        ).reset_index()
        ind_display = ind_display[ind_display["count"] >= 5].sort_values("mean_growth", ascending=False)
        
        # 标记哪些是政策共振行业
        top_inds_list = []
        for _, r in ind_display.head(15).iterrows():
            ind_info = {
                "industry": r["industry"], 
                "growth_score": round(r["mean_growth"], 2), 
                "mean_roe": round(r["mean_roe"], 2),
                "ret_60d": round(r["ret_60d"], 2),
                "stock_count": int(r["count"]),
            }
            if policy_resonance_found and r["industry"] in target_inds:
                ind_info["policy_resonance"] = True  # 标记政策共振
            top_inds_list.append(ind_info)
        result["top_industries"] = top_inds_list

        sub = self._base_filter(df[df["industry"].isin(target_inds)].copy(), date)

        if sub.empty:
            result["notes"].append(f"无满足基本面条件的个股（ROE≥{self.min_roe}%）")
            return result

        # 成长模式放宽技术面要求，允许站不稳MA60（左侧蛰伏）
        # sub = sub[sub["close"] > sub["ma60"]]  # 移除强制MA60要求
        sub = sub[sub["ret_20d_pct"] > -25]  # 放宽跌幅限制，允许深度超跌

        sub["final_score"] = (
            sub["growth_score"] * 1.5  # 基本面权重提升
            + sub["buy_score"].clip(0, 5) * 4.0  # 技术面权重降低
            + sub["ret_20d_pct"].clip(-25, 30) * 0.2  # 动量权重降低
        )
        
        result["notes"].append(f"成长股筛选条件：ROE≥{self.min_roe}%，毛利率优先，全市场选股")
        if self.exclude_industries:
            result["notes"].append(f"已排除防御性行业：{', '.join(self.exclude_industries)}")
        if policy_resonance_found:
            result["notes"].append("【逆向布局模式】优先选择中线超跌 + 政策共振行业")
        
        return self._finish_selection(sub, result, date, metric="final_score", candidate_limit=candidate_limit)

    def _target_industries(self, ind_perf: pd.DataFrame) -> list:
        lo, hi = self.industry_rank_range
        if len(ind_perf) >= hi:
            return ind_perf.iloc[lo - 1:hi]["industry"].tolist()
        return ind_perf.iloc[max(0, lo - 1):]["industry"].tolist()

    def _base_filter(self, sub: pd.DataFrame, date: str) -> pd.DataFrame:
        if sub.empty:
            return sub
        sub = sub[~sub.index.astype(str).str.endswith(".BJ")]
        sub["list_date_int"] = sub.index.map(
            lambda code: int(self.cache.universe.loc[code, "list_date"]) if code in self.cache.universe.index and pd.notna(self.cache.universe.loc[code, "list_date"]) else 0
        )
        sub = sub[int(date) - sub["list_date_int"] > 10000]
        if self.require_dividend:
            sub = sub[sub["has_div"]]
        if self.min_roe > 0:
            sub = sub[sub["latest_roe"] >= self.min_roe]
        if self.exclude_industries:
            sub = sub[~sub["industry"].isin(self.exclude_industries)]
        # 估值过滤：排除价格处于 120 日区间顶部 15% 的股票（过热，追高风险大）
        if "price_120d_pct" in sub.columns:
            original_count = len(sub)
            sub = sub[sub["price_120d_pct"] <= 0.85]
            if len(sub) < original_count:
                pass  # 静默过滤，不污染 notes
        return sub

    def _apply_mode_thresholds(self, sub: pd.DataFrame, result: dict) -> pd.DataFrame:
        """
        解耦打分制：根据不同模式应用不同的准入门槛
        - Growth (成长): 基本面优先，技术面放宽
        - Short (短线): 趋势+量能优先，基本面放宽
        - Swing (波段): 平衡模式，沿用原有标准
        """
        if sub.empty:
            return sub

        original_count = len(sub)

        if self.mode == "growth":
            # 成长模式：基本面硬门槛，技术面放宽
            # 硬门槛: 基本面得分 >= 4 (有分红 + ROE>=15% 或 有分红 + ROE>=10%)
            # 技术面只需 >= 2 分
            sub = sub[sub["buy_score"] >= 2]
            # 基本面隐含条件：min_roe 已经在 _base_filter 中设为 10%
            if len(sub) < original_count:
                result["notes"].append(f"[成长模式] 技术面门槛放宽至 >=2分，过滤 {original_count - len(sub)} 只股票")

        elif self.mode == "short":
            # 短线模式：趋势+量能优先，基本面放宽
            # 硬门槛：趋势分 >= 4，量能分 >= 4
            # 注意：这里需要用 buy_score 作为技术面代理，实际趋势和量能在后续评估中验证
            sub = sub[sub["buy_score"] >= 4]
            # 基本面放宽：min_roe 已经在 _base_filter 中设为 0% (只需 ROE>0)
            if len(sub) < original_count:
                result["notes"].append(f"[短线模式] 技术面门槛提高至 >=4分，过滤 {original_count - len(sub)} 只股票")

        else:  # swing 模式
            # 波段模式：平衡标准
            sub = sub[sub["buy_score"] >= self.min_buy_score]
            if len(sub) < original_count:
                result["notes"].append(f"[波段模式] 技术面门槛 >= {self.min_buy_score}分，过滤 {original_count - len(sub)} 只股票")

        return sub

    def _finish_selection(self, sub: pd.DataFrame, result: dict, date: str, metric: str, candidate_limit: int = 5) -> dict:
        if sub.empty:
            result["notes"].append("选定行业内无符合基本条件的个股")
            return result

        # 趋势过滤（在分位排名之前执行，保持统计意义）
        # 注意：成长模式放宽趋势要求，不强制 MA20 和 MACD
        trend_mode = self.mode == "swing"  # 仅波段模式强制趋势过滤
        if trend_mode and "s_ma20" in sub.columns:
            original_count = len(sub)
            sub = sub[sub["s_ma20"] == 1]
            if original_count > len(sub):
                result["notes"].append(f"过滤掉 {original_count - len(sub)} 只跌破MA20的股票（中期趋势走弱）")

        if trend_mode and "s_macd" in sub.columns:
            original_count = len(sub)
            sub = sub[sub["s_macd"] == 1]
            if original_count > len(sub):
                result["notes"].append(f"过滤掉 {original_count - len(sub)} 只MACD翻绿的股票（动能减弱）")

        # 解耦打分制：根据模式应用不同的技术面门槛
        sub = self._apply_mode_thresholds(sub, result)
        if sub.empty:
            result["notes"].append(f"无个股满足 {self.mode} 模式的准入门槛")
            return result

        rank_metric = metric if metric in sub.columns else "cum_3d_pct"
        sub["pct_rank"] = sub.groupby("industry")[rank_metric].rank(pct=True)
        sub = sub[(sub["pct_rank"] >= self.mid_pct_lo) & (sub["pct_rank"] <= self.mid_pct_hi)]

        if sub.empty:
            result["notes"].append("分位排名筛选后无符合条件的个股")
            return result

        sub = sub.sort_values(["buy_score", rank_metric], ascending=[False, False])
        max_picks = result["position_rule"]["max_picks"]
        result["candidate_pool_size"] = min(candidate_limit, len(sub))

        # 行业分散：同一行业最多选 2 只
        top = []
        industry_count = {}
        for ts_code, row in sub.iterrows():
            ind = row.get("industry", "")
            if industry_count.get(ind, 0) >= 2:
                continue
            industry_count[ind] = industry_count.get(ind, 0) + 1
            top.append((ts_code, row))
            if len(top) >= candidate_limit:
                break

        for rank, (ts_code, row) in enumerate(top, 1):
            result["picks"].append(self._build_pick(ts_code, row, rank, max_picks))
        return result

    def _buy_high(self, close: float, ma5=None, ma10=None, boll_upper=None) -> float:
        """买入区间上限：取最近的技术阻力位"""
        candidates = [close * 1.03]  # 硬上限 +3%
        if boll_upper is not None and boll_upper > close:
            candidates.append(boll_upper)  # 布林上轨
        if ma5 is not None and ma5 > close:
            candidates.append(ma5)  # 5日均线
        if ma10 is not None and ma10 > close:
            candidates.append(ma10)  # 10日均线
        return round(min(candidates), 2)

    def _build_pick(self, ts_code: str, row: pd.Series, rank: int, max_picks: int) -> dict:
        name = self.cache.universe.loc[ts_code, "name"] if ts_code in self.cache.universe.index else "?"
        close = float(row["close"])
        ma20 = float(row["ma20"]) if pd.notna(row["ma20"]) else close
        ma60 = float(row["ma60"]) if pd.notna(row.get("ma60")) else close
        boll_lower = float(row["boll_lower"]) if pd.notna(row.get("boll_lower")) else None
        atr14 = float(row["atr14"]) if pd.notna(row.get("atr14")) and row.get("atr14") > 0 else None
        price_60d_pct = float(row["price_60d_pct"]) if pd.notna(row.get("price_60d_pct")) else None
        price_120d_pct = float(row["price_120d_pct"]) if pd.notna(row.get("price_120d_pct")) else None

        # ATR 动态止损：ATR×1.5 为基准，硬上限防止盈亏比倒挂
        if atr14 is not None:
            atr_stop = round(close - atr14 * 1.5, 2)
        else:
            atr_stop = None

        if self.mode == "short":
            low_60d = float(row["low_60d"]) if pd.notna(row.get("low_60d")) else close
            high_60d = float(row["high_60d"]) if pd.notna(row.get("high_60d")) else None
            # 短线：ATR×1.5 为主，硬上限 -7%，MA20 和 60日低点为辅
            hard_cap = round(close * 0.93, 2)
            candidates = [hard_cap]
            if atr_stop is not None:
                candidates.append(atr_stop)
            candidates.append(ma20 * 0.97)
            if low_60d > 0:
                candidates.append(low_60d * 0.97)
            stop_loss = round(max(candidates), 2)
            target = round(min(close * 1.08, high_60d * 0.98) if high_60d and high_60d > close else close * 1.08, 2)
            second_target = round(close * 1.15, 2)
            hold_period = "2~4 周（短线）"
            buy_high = self._buy_high(close, row.get("ma5"), row.get("ma10"), row.get("boll_upper"))
            buy_range = [round(max(ma20, close * 0.97, low_60d * 1.02), 2), buy_high]
        elif self.mode == "growth":
            low_60d = float(row["low_60d"]) if pd.notna(row.get("low_60d")) else close
            high_60d = float(row["high_60d"]) if pd.notna(row.get("high_60d")) else None
            # 成长：ATR×1.5 为主，硬上限 -12%，MA60 和 60日低点为辅
            hard_cap = round(close * 0.88, 2)
            candidates = [hard_cap]
            if atr_stop is not None:
                candidates.append(atr_stop)
            candidates.append(ma60 * 0.95)
            if low_60d > 0:
                candidates.append(low_60d * 0.95)
            stop_loss = round(max(candidates), 2)
            target = round(min(close * 1.25, high_60d * 0.98) if high_60d and high_60d > close else close * 1.25, 2)
            second_target = round(close * 1.40, 2)
            hold_period = "3~6 个月（中期成长）"
            buy_high = self._buy_high(close, row.get("ma5"), row.get("ma10"), row.get("boll_upper"))
            buy_range = [round(max(ma60, close * 0.92, low_60d * 1.02), 2), buy_high]
        else:
            low_60d = float(row["low_60d"]) if pd.notna(row.get("low_60d")) else close
            high_60d = float(row["high_60d"]) if pd.notna(row.get("high_60d")) else None
            # 波段：ATR×1.5 为主，硬上限 -10%，布林下轨和均线为辅
            hard_cap = round(close * 0.90, 2)
            candidates = [hard_cap]
            if atr_stop is not None:
                candidates.append(atr_stop)
            if boll_lower is not None and boll_lower > 0:
                candidates.append(boll_lower * 0.98)
                buy_low = round(max(ma20 * 0.98, boll_lower, low_60d * 1.02), 2)
            else:
                candidates.append(ma20 * 0.97)
                buy_low = round(max(ma20 * 0.98, close * 0.95, low_60d * 1.02), 2)
            if low_60d > 0:
                candidates.append(low_60d * 0.97)
            stop_loss = round(max(candidates), 2)
            target = round(min(close * 1.15, high_60d * 0.98) if high_60d and high_60d > close else close * 1.15, 2)
            second_target = round(close * 1.25, 2)
            hold_period = "1~3 个月（中期波段）"
            buy_high = self._buy_high(close, row.get("ma5"), row.get("ma10"), row.get("boll_upper"))
            buy_range = [buy_low, buy_high]
        return {
            "rank": rank,
            "actionable": rank <= max_picks,
            "action_note": "可操作" if rank <= max_picks else "观察池",
            "ts_code": ts_code,
            "name": name,
            "industry": row["industry"],
            "close": round(close, 2),
            "cum_3d_pct": round(float(row.get("cum_3d_pct", 0)), 2) if pd.notna(row.get("cum_3d_pct")) else None,
            "ret_20d_pct": round(float(row.get("ret_20d_pct", 0)), 2) if pd.notna(row.get("ret_20d_pct")) else None,
            "ret_60d_pct": round(float(row.get("ret_60d_pct", 0)), 2) if pd.notna(row.get("ret_60d_pct")) else None,
            "buy_score": int(row["buy_score"]),
            "score_details": {
                "price_above_ma20": bool(row["s_ma20"]),
                "macd_positive": bool(row["s_macd"]),
                "kdj_in_range": bool(row["s_kdj"]),
                "rsi_in_range": bool(row["s_rsi"]),
                "below_boll_upper": bool(row["s_boll"]),
            },
            "latest_roe": round(float(row["latest_roe"]), 2) if pd.notna(row["latest_roe"]) else None,
            "buy_range": buy_range,
            "stop_loss": round(stop_loss, 2),
            "target_price": round(target, 2),
            "second_target_price": round(second_target, 2),
            "risk_reward_ratio": round((target - close) / (close - stop_loss), 2) if close > stop_loss else None,
            "hold_period": hold_period,
            "suggested_position": self._suggest_position(close, stop_loss, target),
            "atr14": round(atr14, 2) if atr14 else None,
            "price_60d_pct": round(price_60d_pct, 2) if price_60d_pct is not None else None,
            "price_120d_pct": round(price_120d_pct, 2) if price_120d_pct is not None else None,
        }

    def _suggest_position(self, close: float, stop_loss: float, target: float) -> dict:
        rr = round((target - close) / (close - stop_loss), 2) if close > stop_loss else 0
        if rr >= 3.0:
            pct = 20
            note = "高盈亏比，可给足仓位"
        elif rr >= 2.0:
            pct = 15
            note = "盈亏比优秀，标准仓位"
        elif rr >= 1.5:
            pct = 10
            note = "盈亏比合理，适中仓位"
        elif rr >= 1.0:
            pct = 5
            note = "盈亏比偏低，轻仓试探"
        else:
            pct = 3
            note = "盈亏比不佳，迷你仓位或观望"
        return {"pct": pct, "note": note}
