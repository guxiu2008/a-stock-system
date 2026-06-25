#!/usr/bin/env python3
"""
实盘数据缓存：只加载最近 120 个交易日的数据供当日分析使用
"""
import os
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

DEFAULT_DB = os.getenv("STOCK_DB_PATH", "/workspace/stock_downloader/stock_data.db")


class LiveCache:
    def __init__(self, db_path: str = None, lookback_days: int = 120):
        self.db_path = db_path or DEFAULT_DB
        self.conn = sqlite3.connect(self.db_path)
        self.lookback_days = lookback_days
        self._load()

    def _load(self):
        # 最新交易日
        cur = self.conn.execute("SELECT MAX(trade_date) FROM fact_daily_quotes")
        self.latest_date = cur.fetchone()[0]

        cur = self.conn.execute(
            "SELECT DISTINCT trade_date FROM fact_daily_quotes ORDER BY trade_date DESC LIMIT 1"
        )
        self.today = cur.fetchone()[0]

        # 取最近 lookback_days 个交易日
        cur = self.conn.execute(
            "SELECT DISTINCT cal_date FROM dim_trade_calendar WHERE cal_date <= ? AND is_open=1 ORDER BY cal_date DESC LIMIT ?",
            (self.latest_date, self.lookback_days)
        )
        self.trade_dates = sorted([r[0] for r in cur.fetchall()])
        start_date = self.trade_dates[0]

        # 股票元数据
        self.universe = pd.read_sql_query("""
            SELECT ts_code, name, industry, list_date
            FROM dim_stock_info
            WHERE list_status = 'L'
              AND name NOT LIKE '%ST%'
              AND name NOT LIKE '%*ST%'
              AND industry IS NOT NULL AND industry != ''
        """, self.conn).set_index("ts_code")

        # 分红和财务指标预加载
        cur = self.conn.execute(
            "SELECT ts_code, COUNT(*) FROM fact_dividend_history GROUP BY ts_code"
        )
        self.has_div = {r[0]: True for r in cur.fetchall()}

        cur = self.conn.execute("""
            SELECT ts_code, roe, grossprofit_margin, netprofit_margin, net_profit
            FROM fact_financial_reports
            WHERE roe IS NOT NULL AND (ann_date IS NULL OR ann_date <= ?)
            ORDER BY end_date DESC
        """, (self.latest_date,))
        self.latest_roe = {}
        self.gross_margin = {}
        self.net_margin = {}
        self.net_profit = {}
        seen = set()
        for ts_code, roe, gm, nm, np in cur.fetchall():
            if ts_code not in seen:
                self.latest_roe[ts_code] = roe
                self.gross_margin[ts_code] = gm
                self.net_margin[ts_code] = nm
                self.net_profit[ts_code] = np
                seen.add(ts_code)

        # 行情 + 指标（最近 N 天）
        self.quotes = pd.read_sql_query("""
            SELECT q.ts_code, q.trade_date, q.open, q.high, q.low, q.close, q.pct_chg, q.vol,
                   mi.ma5, mi.ma10, mi.ma20, mi.ma60,
                   mi.macd, mi.macd_hist, mi.kdj_j, mi.kdj_k, mi.kdj_d, mi.rsi6, mi.boll_upper, mi.boll_lower
            FROM fact_daily_quotes q
            LEFT JOIN market_indicators mi ON q.ts_code = mi.ts_code AND q.trade_date = mi.trade_date
            WHERE q.trade_date >= ? AND q.trade_date <= ?
        """, self.conn, params=(start_date, self.latest_date))

        self.quotes["trade_date"] = self.quotes["trade_date"].astype(str)

        # 合并 meta
        meta = self.universe[["industry"]].reset_index()
        self.quotes = self.quotes.merge(meta, on="ts_code", how="left")
        self.quotes["has_div"] = self.quotes["ts_code"].map(lambda x: self.has_div.get(x, False))
        self.quotes["latest_roe"] = self.quotes["ts_code"].map(lambda x: self.latest_roe.get(x))
        self.quotes["gross_margin"] = self.quotes["ts_code"].map(lambda x: self.gross_margin.get(x))
        self.quotes["net_margin"] = self.quotes["ts_code"].map(lambda x: self.net_margin.get(x))
        self.quotes["net_profit"] = self.quotes["ts_code"].map(lambda x: self.net_profit.get(x))
        self.quotes = self.quotes.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)

        # 预计算短线/中期动量
        grouped = self.quotes.groupby("ts_code")
        self.quotes["cum_3d_pct"] = grouped["pct_chg"].transform(
            lambda s: s.rolling(3, min_periods=3).sum()
        )
        self.quotes["ret_20d_pct"] = grouped["close"].transform(lambda s: (s / s.shift(20) - 1) * 100)
        self.quotes["ret_60d_pct"] = grouped["close"].transform(lambda s: (s / s.shift(60) - 1) * 100)
        self.quotes["low_60d"] = grouped["low"].transform(lambda s: s.rolling(60, min_periods=20).min())
        self.quotes["high_60d"] = grouped["high"].transform(lambda s: s.rolling(60, min_periods=20).max())
        self.quotes["dist_60d_low_pct"] = (self.quotes["close"] / self.quotes["low_60d"] - 1) * 100
        self.quotes["dist_60d_high_pct"] = (self.quotes["close"] / self.quotes["high_60d"] - 1) * 100
        vol_5d = grouped["vol"].transform(lambda s: s.rolling(5, min_periods=3).mean())
        vol_20d = grouped["vol"].transform(lambda s: s.rolling(20, min_periods=10).mean())
        self.quotes["vol_ratio_5_20"] = vol_5d / vol_20d

        # 预计算买入信号
        self.quotes["s_ma20"] = (self.quotes["close"] > self.quotes["ma20"]).astype("int8")
        # MACD: >0 + 柱状>0 + 柱状没有连续2天收缩超过30%（避免动能衰竭）
        self.quotes["macd_hist_prev"] = grouped["macd_hist"].shift(1)
        self.quotes["macd_hist_prev2"] = grouped["macd_hist"].shift(2)
        self.quotes["s_macd"] = (
            (self.quotes["macd"] > 0)
            & (self.quotes["macd_hist"] > 0)
            & ~(
                (self.quotes["macd_hist_prev"] > 0)
                & (self.quotes["macd_hist"] < self.quotes["macd_hist_prev"] * 0.7)
                & (self.quotes["macd_hist_prev"] < self.quotes["macd_hist_prev2"] * 0.7)
            )
        ).astype("int8")
        # KDJ: J在20~80之间 + K>D(多头排列) + J没有3天内从>80急跌到<60(避免高位死叉)
        self.quotes["kdj_j_3d_ago"] = grouped["kdj_j"].shift(3)
        self.quotes["s_kdj"] = (
            (self.quotes["kdj_j"] >= 20) & (self.quotes["kdj_j"] <= 80)
            & (self.quotes["kdj_k"] > self.quotes["kdj_d"])
            & ~((self.quotes["kdj_j_3d_ago"] > 80) & (self.quotes["kdj_j"] < 60))
        ).astype("int8")
        self.quotes["s_rsi"] = ((self.quotes["rsi6"] >= 30) & (self.quotes["rsi6"] <= 70)).astype("int8")
        self.quotes["s_boll"] = (self.quotes["close"] < self.quotes["boll_upper"]).astype("int8")
        self.quotes["buy_score"] = (
            self.quotes["s_ma20"] + self.quotes["s_macd"] + self.quotes["s_kdj"]
            + self.quotes["s_rsi"] + self.quotes["s_boll"]
        )

        # 索引加速
        self.quotes = self.quotes.set_index(["trade_date", "ts_code"]).sort_index()
        self.by_code = self.quotes.swaplevel().sort_index()

        # 大盘趋势和情绪指标
        idx_df = pd.read_sql_query("""
            SELECT q.trade_date, q.close, q.pct_chg, q.vol, 
                   mi.ma5, mi.ma10, mi.ma20, mi.ma60,
                   mi.macd, mi.macd_hist, mi.rsi6, mi.rsi12, mi.rsi24
            FROM fact_index_daily q
            LEFT JOIN market_indicators mi ON q.ts_code = mi.ts_code AND q.trade_date = mi.trade_date
            WHERE q.ts_code = '000001.SH' AND q.trade_date >= ?
        """, self.conn, params=(start_date,))
        idx_df["trade_date"] = idx_df["trade_date"].astype(str)
        idx_df["trend"] = "震荡市"
        idx_df.loc[(idx_df["close"] > idx_df["ma20"]) & (idx_df["ma5"] > idx_df["ma10"]), "trend"] = "上升趋势"
        idx_df.loc[(idx_df["close"] < idx_df["ma20"]) & (idx_df["ma5"] < idx_df["ma10"]), "trend"] = "下跌趋势"
        idx_df.loc[idx_df["ma20"].isna(), "trend"] = "unknown"
        
        # RSI超买超卖信号
        idx_df["rsi_signal"] = "正常"
        idx_df.loc[idx_df["rsi6"] >= 80, "rsi_signal"] = "极度超买"
        idx_df.loc[(idx_df["rsi6"] >= 70) & (idx_df["rsi6"] < 80), "rsi_signal"] = "超买"
        idx_df.loc[(idx_df["rsi6"] <= 20), "rsi_signal"] = "极度超卖"
        idx_df.loc[(idx_df["rsi6"] > 20) & (idx_df["rsi6"] <= 30), "rsi_signal"] = "超卖"
        
        # 情绪温度计 0-100
        idx_df["sentiment"] = 50  # 中性
        idx_df.loc[idx_df["rsi6"] >= 80, "sentiment"] = 95
        idx_df.loc[(idx_df["rsi6"] >= 70) & (idx_df["rsi6"] < 80), "sentiment"] = 80
        idx_df.loc[(idx_df["rsi6"] >= 60) & (idx_df["rsi6"] < 70), "sentiment"] = 65
        idx_df.loc[(idx_df["rsi6"] > 30) & (idx_df["rsi6"] < 40), "sentiment"] = 35
        idx_df.loc[(idx_df["rsi6"] > 20) & (idx_df["rsi6"] <= 30), "sentiment"] = 20
        idx_df.loc[idx_df["rsi6"] <= 20, "sentiment"] = 5
        
        # 极端涨跌幅标记
        idx_df["extreme_move"] = False
        idx_df.loc[idx_df["pct_chg"].abs() >= 3, "extreme_move"] = True
        
        # 趋势变化检测
        idx_df["prev_trend"] = idx_df["trend"].shift(-1)
        idx_df["trend_change"] = "不变"
        idx_df.loc[(idx_df["prev_trend"] == "下跌趋势") & (idx_df["trend"] == "震荡市"), "trend_change"] = "止跌企稳"
        idx_df.loc[(idx_df["prev_trend"] == "下跌趋势") & (idx_df["trend"] == "上升趋势"), "trend_change"] = "趋势反转向上"
        idx_df.loc[(idx_df["prev_trend"] == "震荡市") & (idx_df["trend"] == "上升趋势"), "trend_change"] = "突破向上"
        idx_df.loc[(idx_df["prev_trend"] == "上升趋势") & (idx_df["trend"] == "震荡市"), "trend_change"] = "上升遇阻"
        idx_df.loc[(idx_df["prev_trend"] == "震荡市") & (idx_df["trend"] == "下跌趋势"), "trend_change"] = "破位向下"
        idx_df.loc[(idx_df["prev_trend"] == "上升趋势") & (idx_df["trend"] == "下跌趋势"), "trend_change"] = "趋势反转向下"
        
        # MACD金叉死叉
        idx_df["macd_gold_cross"] = (idx_df["macd"] > 0) & (idx_df["macd"].shift(-1) <= 0)
        idx_df["macd_death_cross"] = (idx_df["macd"] < 0) & (idx_df["macd"].shift(-1) >= 0)
        idx_df["macd_red"] = idx_df["macd_hist"] > 0  # 柱状翻红
        
        # 连续上涨/下跌天数
        idx_df["consecutive_up"] = (idx_df["pct_chg"] > 0).astype(int).groupby(
            (idx_df["pct_chg"] <= 0).cumsum()).cumsum()
        idx_df["consecutive_down"] = (idx_df["pct_chg"] < 0).astype(int).groupby(
            (idx_df["pct_chg"] >= 0).cumsum()).cumsum()
        
        self.trend_map = dict(zip(idx_df["trade_date"], idx_df["trend"]))
        self.rsi_signal_map = dict(zip(idx_df["trade_date"], idx_df["rsi_signal"]))
        self.sentiment_map = dict(zip(idx_df["trade_date"], idx_df["sentiment"]))
        self.extreme_move_map = dict(zip(idx_df["trade_date"], idx_df["extreme_move"]))
        self.trend_change_map = dict(zip(idx_df["trade_date"], idx_df["trend_change"]))
        self.macd_gold_cross_map = dict(zip(idx_df["trade_date"], idx_df["macd_gold_cross"]))
        self.macd_red_map = dict(zip(idx_df["trade_date"], idx_df["macd_red"]))
        self.consecutive_up_map = dict(zip(idx_df["trade_date"], idx_df["consecutive_up"]))
        self.consecutive_down_map = dict(zip(idx_df["trade_date"], idx_df["consecutive_down"]))
        self.idx_close = dict(zip(idx_df["trade_date"], idx_df["close"]))
        self.idx_rsi = dict(zip(idx_df["trade_date"], idx_df["rsi6"]))
        self.idx_pct = dict(zip(idx_df["trade_date"], idx_df["pct_chg"]))

    def daily(self, date: str = None):
        date = date or self.latest_date
        try:
            return self.quotes.loc[date]
        except KeyError:
            return pd.DataFrame()

    def stock(self, ts_code: str, date: str = None):
        date = date or self.latest_date
        try:
            return self.by_code.loc[(ts_code, date)]
        except KeyError:
            return None

    def stock_history(self, ts_code: str, n: int = 30):
        """获取最近 N 天历史"""
        try:
            sub = self.by_code.loc[ts_code].sort_index()
            return sub.tail(n)
        except KeyError:
            return pd.DataFrame()

    def trend(self, date: str = None) -> str:
        date = date or self.latest_date
        return self.trend_map.get(date, "unknown")

    def rsi_signal(self, date: str = None) -> str:
        date = date or self.latest_date
        return self.rsi_signal_map.get(date, "正常")

    def sentiment(self, date: str = None) -> int:
        date = date or self.latest_date
        return self.sentiment_map.get(date, 50)

    def is_extreme_move(self, date: str = None) -> bool:
        date = date or self.latest_date
        return self.extreme_move_map.get(date, False)

    def index_rsi(self, date: str = None) -> float:
        date = date or self.latest_date
        return self.idx_rsi.get(date, 50)

    def index_pct(self, date: str = None) -> float:
        date = date or self.latest_date
        return self.idx_pct.get(date, 0)

    def trend_change(self, date: str = None) -> str:
        date = date or self.latest_date
        return self.trend_change_map.get(date, "不变")

    def is_macd_gold_cross(self, date: str = None) -> bool:
        date = date or self.latest_date
        return self.macd_gold_cross_map.get(date, False)

    def is_macd_red(self, date: str = None) -> bool:
        date = date or self.latest_date
        return self.macd_red_map.get(date, False)

    def consecutive_up_days(self, date: str = None) -> int:
        date = date or self.latest_date
        return int(self.consecutive_up_map.get(date, 0))

    def consecutive_down_days(self, date: str = None) -> int:
        date = date or self.latest_date
        return int(self.consecutive_down_map.get(date, 0))

    def get_market_forecast(self, date: str = None) -> dict:
        """生成明日大盘预测"""
        date = date or self.latest_date
        trend = self.trend(date)
        rsi = self.index_rsi(date)
        rsi_signal = self.rsi_signal(date)
        trend_change = self.trend_change(date)
        consecutive_up = self.consecutive_up_days(date)
        consecutive_down = self.consecutive_down_days(date)
        pct = self.index_pct(date)
        is_macd_red = self.is_macd_red(date)
        
        bullish_signals = 0
        bearish_signals = 0
        
        if trend == "上升趋势":
            bullish_signals += 2
        elif trend == "下跌趋势":
            bearish_signals += 2
        
        if trend_change in ["趋势反转向上", "突破向上", "止跌企稳"]:
            bullish_signals += 3
        elif trend_change in ["趋势反转向下", "破位向下", "上升遇阻"]:
            bearish_signals += 3
        
        if rsi_signal in ["极度超卖", "超卖"]:
            bullish_signals += 2
        elif rsi_signal in ["极度超买", "超买"]:
            bearish_signals += 2
        
        if consecutive_up >= 3:
            bearish_signals += 1
        elif consecutive_down >= 3:
            bullish_signals += 1
        
        if is_macd_red:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        if pct > 1.5 and rsi > 75:
            bearish_signals += 2
        
        score = 50 + (bullish_signals - bearish_signals) * 8
        score = max(5, min(95, score))
        
        if score >= 75:
            direction = "📈 看涨"
            confidence = "高"
        elif score >= 60:
            direction = "↗️ 偏多"
            confidence = "中高"
        elif score >= 45:
            direction = "➡️ 震荡"
            confidence = "中"
        elif score >= 30:
            direction = "↘️ 偏空"
            confidence = "中高"
        else:
            direction = "📉 看跌"
            confidence = "高"
        
        return {
            "score": score,
            "direction": direction,
            "confidence": confidence,
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals,
            "trend": trend,
            "trend_change": trend_change,
            "rsi": rsi,
            "rsi_signal": rsi_signal,
            "consecutive_up": consecutive_up,
            "consecutive_down": consecutive_down,
            "is_macd_red": is_macd_red,
        }

    def close(self):
        self.conn.close()
