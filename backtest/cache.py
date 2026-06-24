#!/usr/bin/env python3
"""
预加载全市场数据到内存，加速回测。一次性加载 + 向量化预计算。
"""
import sqlite3
import os
import pandas as pd
import numpy as np
from pathlib import Path

DB_PATH = os.getenv("STOCK_DB_PATH", "/workspace/stock_downloader/stock_data.db")


class MarketCache:
    def __init__(self, start_date="20221001", end_date="20260605"):
        self.start_date = start_date
        self.end_date = end_date
        self.conn = sqlite3.connect(DB_PATH)
        print(f"[Cache] Loading {start_date} ~ {end_date}...")
        self._load_all()
        self._precompute()
        self.conn.close()
        print("[Cache] Ready.")

    def _load_all(self):
        print("  - universe...", end=" ", flush=True)
        self.universe = pd.read_sql_query("""
            SELECT s.ts_code, s.name, s.industry, s.list_date,
                   (SELECT COUNT(*) FROM fact_dividend_history h WHERE h.ts_code = s.ts_code) as div_count,
                   (SELECT roe FROM fact_financial_reports r WHERE r.ts_code = s.ts_code AND r.roe IS NOT NULL ORDER BY r.end_date DESC LIMIT 1) as latest_roe
            FROM dim_stock_info s
            WHERE s.list_status = 'L'
              AND s.name NOT LIKE '%ST%'
              AND s.name NOT LIKE '%*ST%'
              AND s.industry IS NOT NULL AND s.industry != ''
        """, self.conn)
        self.universe["has_div"] = self.universe["div_count"] > 0
        self.universe = self.universe.set_index("ts_code")
        print(f"{len(self.universe)} stocks")

        print("  - quotes + indicators (joined SQL)...", end=" ", flush=True)
        # 一次 JOIN 拉完所有需要的列，避免后续 merge
        sql = """
        SELECT q.ts_code, q.trade_date, q.open, q.high, q.low, q.close, q.pct_chg, q.vol,
               mi.ma5, mi.ma10, mi.ma20, mi.ma60,
               mi.macd, mi.macd_hist, mi.kdj_j, mi.rsi6, mi.boll_upper
        FROM fact_daily_quotes q
        LEFT JOIN market_indicators mi
          ON q.ts_code = mi.ts_code AND q.trade_date = mi.trade_date
        WHERE q.trade_date BETWEEN ? AND ?
        """
        df = pd.read_sql_query(sql, self.conn, params=(self.start_date, self.end_date))
        df["trade_date"] = df["trade_date"].astype(str)
        # 只保留 universe 内的股票（自动过滤 ST/无行业）
        df = df[df["ts_code"].isin(self.universe.index)]
        print(f"{len(df):,} rows")

        # merge industry/has_div/roe/list_date
        meta = self.universe[["industry", "has_div", "latest_roe", "list_date"]].reset_index()
        df = df.merge(meta, on="ts_code", how="left")
        df["list_date"] = pd.to_numeric(df["list_date"], errors="coerce")
        df["trade_date_int"] = pd.to_numeric(df["trade_date"])
        # 排序很重要
        df = df.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
        self.full = df

        # 大盘指数
        print("  - index data...", end=" ", flush=True)
        self.index_data = pd.read_sql_query("""
            SELECT q.ts_code, q.trade_date, q.close, q.pct_chg,
                   mi.ma5, mi.ma10, mi.ma20, mi.ma60
            FROM fact_index_daily q
            LEFT JOIN market_indicators mi
              ON q.ts_code = mi.ts_code AND q.trade_date = mi.trade_date
            WHERE q.ts_code IN ('000001.SH', '000300.SH')
              AND q.trade_date BETWEEN ? AND ?
        """, self.conn, params=(self.start_date, self.end_date))
        self.index_data["trade_date"] = self.index_data["trade_date"].astype(str)
        print(f"{len(self.index_data)} rows")

        # 交易日
        cur = self.conn.execute(
            "SELECT DISTINCT cal_date FROM dim_trade_calendar "
            "WHERE cal_date BETWEEN ? AND ? AND is_open=1 ORDER BY cal_date",
            (self.start_date, self.end_date)
        )
        self.trade_dates = [r[0] for r in cur.fetchall()]
        self.date_to_idx = {d: i for i, d in enumerate(self.trade_dates)}
        print(f"  - {len(self.trade_dates)} trade dates")

    def _precompute(self):
        """向量化预计算: 3日累计涨幅、买入打分、按日期分组索引"""
        print("  - precomputing 3d cum_pct...", end=" ", flush=True)
        df = self.full
        df["cum_3d_pct"] = df.groupby("ts_code")["pct_chg"].transform(
            lambda s: s.rolling(3, min_periods=3).sum()
        )
        print("done")

        print("  - precomputing buy_score...", end=" ", flush=True)
        df["s_ma20"] = (df["close"] > df["ma20"]).astype("int8")
        df["s_macd"] = ((df["macd"] > 0) & (df["macd_hist"] > 0)).astype("int8")
        df["s_kdj"] = ((df["kdj_j"] >= 20) & (df["kdj_j"] <= 80)).astype("int8")
        df["s_rsi"] = ((df["rsi6"] >= 30) & (df["rsi6"] <= 70)).astype("int8")
        df["s_boll"] = (df["close"] < df["boll_upper"]).astype("int8")
        df["buy_score"] = df["s_ma20"] + df["s_macd"] + df["s_kdj"] + df["s_rsi"] + df["s_boll"]
        print("done")

        print("  - building date -> rows index...", end=" ", flush=True)
        # 关键加速：按日期分组（多重索引）方便 O(1) 取当日所有行
        df = df.set_index(["trade_date", "ts_code"]).sort_index()
        self.full_indexed = df
        # 同时建一个 (ts_code, trade_date) 的 lookup（按ts_code查时间序列）
        self.by_code = df.swaplevel().sort_index()
        # 当日数据按 date 分组缓存，避免重复 .loc
        self.daily_groups = {}
        # 不在这里建全部 daily group（会很慢且占内存），用时再建
        print("done")

        # 指数趋势预计算
        print("  - precomputing index trend...", end=" ", flush=True)
        sh = self.index_data[self.index_data["ts_code"] == "000001.SH"].copy()
        sh["trend"] = "震荡市"
        sh.loc[(sh["close"] > sh["ma20"]) & (sh["ma5"] > sh["ma10"]), "trend"] = "上升趋势"
        sh.loc[(sh["close"] < sh["ma20"]) & (sh["ma5"] < sh["ma10"]), "trend"] = "下跌趋势"
        sh.loc[sh["ma20"].isna(), "trend"] = "unknown"
        self.trend_by_date = dict(zip(sh["trade_date"], sh["trend"]))
        print("done")

    def daily(self, date: str) -> pd.DataFrame:
        """O(1)取某日所有股票（用 multi-index .loc）"""
        try:
            return self.full_indexed.loc[date]
        except KeyError:
            return pd.DataFrame()

    def stock_row(self, ts_code: str, date: str):
        """单股单日数据"""
        try:
            return self.by_code.loc[(ts_code, date)]
        except KeyError:
            return None

    def stock_next_open(self, ts_code: str, date: str):
        """T+1 开盘价"""
        idx = self.date_to_idx.get(date)
        if idx is None or idx >= len(self.trade_dates) - 1:
            return None
        next_date = self.trade_dates[idx + 1]
        row = self.stock_row(ts_code, next_date)
        return row["open"] if row is not None else None

    def trend(self, date: str) -> str:
        return self.trend_by_date.get(date, "unknown")


if __name__ == "__main__":
    c = MarketCache("20221001", "20260605")
    import time
    t0 = time.time()
    df = c.daily("20250320")
    print(f"daily('20250320') -> {len(df)} rows in {(time.time()-t0)*1000:.2f}ms")
    t0 = time.time()
    for d in c.trade_dates[-100:]:
        _ = c.daily(d)
    print(f"100 daily lookups in {(time.time()-t0)*1000:.2f}ms")
    print(f"Sample buy_score distribution on 20250320:")
    print(df["buy_score"].value_counts().sort_index())