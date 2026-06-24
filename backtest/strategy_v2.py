#!/usr/bin/env python3
"""
v2 七步法策略 - 完全向量化，依赖 cache 预计算
"""
import pandas as pd
import numpy as np


class V2Strategy:
    def __init__(self, cache,
                 industry_rank_range=(3, 12),
                 max_industry_3d_pct=15.0,
                 min_buy_score=3,
                 min_roe=5.0,
                 require_dividend=True,
                 mid_pct_lo=0.3,
                 mid_pct_hi=0.7):
        self.cache = cache
        self.industry_rank_range = industry_rank_range
        self.max_industry_3d_pct = max_industry_3d_pct
        self.min_buy_score = min_buy_score
        self.min_roe = min_roe
        self.require_dividend = require_dividend
        self.mid_pct_lo = mid_pct_lo
        self.mid_pct_hi = mid_pct_hi

    def _get_trend(self, date):
        return self.cache.trend(date)

    def _get_position(self, trend):
        m = {
            "上升趋势": (0.8, 0.20, 3),
            "震荡市":   (0.5, 0.15, 2),
            "下跌趋势": (0.2, 0.10, 1),
            "unknown":  (0.3, 0.15, 1),
        }
        return m.get(trend, (0.3, 0.15, 1))

    def select_stocks(self, date):
        trend = self._get_trend(date)
        if trend == "unknown":
            return []
        _, _, max_picks = self._get_position(trend)

        df = self.cache.daily(date)  # multi-index loc[date] -> ts_code-indexed frame
        if df.empty:
            return []

        # 必须有 3 日累计涨幅
        df = df.dropna(subset=["cum_3d_pct"])
        if df.empty:
            return []

        # 行业 3 日平均涨幅排名
        ind_perf = df.groupby("industry")["cum_3d_pct"].agg(["mean", "count"]).reset_index()
        ind_perf = ind_perf[ind_perf["count"] >= 5]  # 至少 5 只
        ind_perf = ind_perf[ind_perf["mean"] <= self.max_industry_3d_pct]
        ind_perf = ind_perf.sort_values("mean", ascending=False)

        if ind_perf.empty:
            return []

        lo, hi = self.industry_rank_range
        if len(ind_perf) >= hi:
            target_inds = ind_perf.iloc[lo - 1:hi]["industry"].tolist()
        else:
            target_inds = ind_perf.iloc[max(0, lo - 1):]["industry"].tolist()

        if not target_inds:
            return []

        # 个股筛选
        sub = df[df["industry"].isin(target_inds)].copy()
        # 上市 > 1 年
        sub = sub[sub["trade_date_int"] - sub["list_date"] > 10000]
        if self.require_dividend:
            sub = sub[sub["has_div"]]
        if self.min_roe > 0:
            sub = sub[sub["latest_roe"] >= self.min_roe]
        # 3 日累计涨幅 > 0
        sub = sub[sub["cum_3d_pct"] > 0]

        if sub.empty:
            return []

        # 板块内中位段
        sub["pct_rank"] = sub.groupby("industry")["cum_3d_pct"].rank(pct=True)
        sub = sub[(sub["pct_rank"] >= self.mid_pct_lo) & (sub["pct_rank"] <= self.mid_pct_hi)]

        # 打分过滤
        sub = sub[sub["buy_score"] >= self.min_buy_score]

        if sub.empty:
            return []

        # 排序：打分 desc, cum_3d desc
        sub = sub.sort_values(["buy_score", "cum_3d_pct"], ascending=[False, False])
        top = sub.head(max_picks * 2)

        # 此时 sub 的 index 是 ts_code（因为 multi-index .loc[date] 返回单层）
        results = []
        for ts_code, row in top.iterrows():
            results.append({
                "ts_code": ts_code,
                "name": self.cache.universe.loc[ts_code, "name"] if ts_code in self.cache.universe.index else "?",
                "industry": row["industry"],
                "cum_3d_pct": round(float(row["cum_3d_pct"]), 2),
                "buy_score": int(row["buy_score"]),
                "roe": round(float(row["latest_roe"]), 2) if pd.notna(row["latest_roe"]) else None,
                "close": round(float(row["close"]), 2),
                "ma20": float(row["ma20"]) if pd.notna(row["ma20"]) else None,
                "trend": trend,
            })
        return results[:max_picks]


if __name__ == "__main__":
    import sys, time
    sys.path.insert(0, "/tmp/backtest")
    from cache import MarketCache
    cache = MarketCache("20221001", "20260605")
    s = V2Strategy(cache)
    t0 = time.time()
    total = 0
    for d in cache.trade_dates[-100:]:
        picks = s.select_stocks(d)
        total += len(picks)
    print(f"100 days, {total} picks, {(time.time()-t0)*1000:.0f}ms total, {(time.time()-t0)*10:.2f}ms/day")