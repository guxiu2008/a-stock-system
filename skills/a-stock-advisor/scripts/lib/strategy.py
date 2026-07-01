#!/usr/bin/env python3
"""
v2 七步法选股策略 - 实盘版
支持三种模式：
- short:  2~4 周，目标 +8%，偏短线波段（技术面驱动）
- swing:  1~3 个月，目标 +15~25%，偏中期波段（技术+行业轮动）
- growth: 3~6 个月，目标 +30~50%，偏中期成长（基本面驱动，ROE优先）
"""
import pandas as pd
import numpy as np


OPTIMAL_PARAMS = {
    "mode": "short",
    "industry_rank_range": (3, 12),
    "max_industry_3d_pct": 15.0,
    "min_buy_score": 4,
    "min_roe": 0.0,
    "require_dividend": True,
    "mid_pct_lo": 0.3,
    "mid_pct_hi": 0.7,
}


SWING_PARAMS = {
    "mode": "swing",
    "industry_rank_range": (3, 15),
    "min_buy_score": 4,
    "min_roe": 1.0,
    "require_dividend": True,
    "mid_pct_lo": 0.25,
    "mid_pct_hi": 0.75,
}


GROWTH_PARAMS = {
    "mode": "growth",
    "industry_rank_range": (1, 20),
    "min_buy_score": 4,
    "min_roe": 10.0,
    "require_dividend": False,
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
            "position_rule": get_position_rule(trend, rsi_signal, sentiment, extreme_move),
            "top_industries": [],
            "picks": [],
            "notes": [],
        }

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
        ind_perf = df.groupby("industry")["cum_3d_pct"].agg(["mean", "count"]).reset_index()
        ind_perf = ind_perf[ind_perf["count"] >= 5]
        ind_perf = ind_perf[ind_perf["mean"] <= self.max_industry_3d_pct]
        ind_perf = ind_perf.sort_values("mean", ascending=False).reset_index(drop=True)
        result["top_industries"] = [
            {"industry": r["industry"], "score": round(r["mean"], 2), "stock_count": int(r["count"])}
            for _, r in ind_perf.head(15).iterrows()
        ]
        if ind_perf.empty:
            result["notes"].append("无有效行业（可能是大盘极弱）")
            return result
        target_inds = self._target_industries(ind_perf)
        sub = self._base_filter(df[df["industry"].isin(target_inds)].copy(), date)
        sub = sub[sub["cum_3d_pct"] > 0]
        sub = sub[sub["close"] > sub["ma20"]]
        return self._finish_selection(sub, result, date, metric="cum_3d_pct", candidate_limit=candidate_limit)

    def _select_swing(self, df: pd.DataFrame, result: dict, date: str, candidate_limit: int = 5) -> dict:
        df = df.dropna(subset=["ret_20d_pct", "ret_60d_pct", "ma60"])
        df = df.copy()
        df["industry_strength"] = df["ret_20d_pct"] * 0.6 + df["ret_60d_pct"] * 0.4
        ind_perf = df.groupby("industry").agg(
            mean=("industry_strength", "mean"),
            ret20=("ret_20d_pct", "mean"),
            ret60=("ret_60d_pct", "mean"),
            count=("industry", "count"),
        ).reset_index()
        ind_perf = ind_perf[(ind_perf["count"] >= 5) & (ind_perf["ret20"] > -5) & (ind_perf["ret60"] > -15)]
        ind_perf = ind_perf.sort_values("mean", ascending=False).reset_index(drop=True)
        result["top_industries"] = [
            {"industry": r["industry"], "score": round(r["mean"], 2), "ret20": round(r["ret20"], 2), "ret60": round(r["ret60"], 2), "stock_count": int(r["count"])}
            for _, r in ind_perf.head(15).iterrows()
        ]
        if ind_perf.empty:
            result["notes"].append("无有效中期趋势行业")
            return result
        target_inds = self._target_industries(ind_perf)
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
        """中期成长策略：基本面优先，技术面辅助，目标30~50%收益"""
        df = df.dropna(subset=["latest_roe", "gross_margin", "ma60"])
        
        df["growth_score"] = (
            df["latest_roe"].clip(0, 40) * 2.5
            + df["gross_margin"].fillna(0).clip(0, 80) * 0.6
            + df["net_margin"].fillna(0).clip(0, 50) * 0.4
        )

        ind_perf = df.groupby("industry").agg(
            mean_growth=("growth_score", "mean"),
            mean_roe=("latest_roe", "mean"),
            count=("industry", "count"),
            high_roe_cnt=("latest_roe", lambda x: (x >= self.min_roe).sum()),
        ).reset_index()
        ind_perf = ind_perf[ind_perf["count"] >= 5]
        ind_perf = ind_perf.sort_values("high_roe_cnt", ascending=False).reset_index(drop=True)
        result["top_industries"] = [
            {"industry": r["industry"], "growth_score": round(r["mean_growth"], 2), "mean_roe": round(r["mean_roe"], 2), "stock_count": int(r["count"])}
            for _, r in ind_perf.head(15).iterrows()
        ]

        sub = self._base_filter(df.copy(), date)

        if sub.empty:
            result["notes"].append(f"无满足基本面条件的个股（ROE≥{self.min_roe}%）")
            return result

        sub = sub[sub["close"] > sub["ma60"]]
        sub = sub[sub["ret_20d_pct"] > -15]

        sub["final_score"] = (
            sub["growth_score"] * 1.2
            + sub["buy_score"].clip(0, 5) * 6.0
            + sub["ret_20d_pct"].clip(-15, 30) * 0.3
        )
        
        result["notes"].append(f"成长股筛选条件：ROE≥{self.min_roe}%，毛利率优先，全市场选股")
        result["notes"].append(f"已排除防御性行业：{', '.join(self.exclude_industries)}")
        
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

    def _finish_selection(self, sub: pd.DataFrame, result: dict, date: str, metric: str, candidate_limit: int = 5) -> dict:
        if sub.empty:
            result["notes"].append("选定行业内无符合基本条件的个股")
            return result

        # 趋势过滤（在分位排名之前执行，保持统计意义）
        trend_mode = self.mode in ["swing", "growth"]
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

        sub = sub[sub["buy_score"] >= self.min_buy_score]
        if sub.empty:
            result["notes"].append(f"无个股技术面信号足够强（打分 >= {self.min_buy_score}）")
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
