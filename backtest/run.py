#!/usr/bin/env python3
"""
回测主入口：加载数据 → 策略选股 → 模拟交易 → 输出报告
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd
from cache import MarketCache
from strategy_v2 import V2Strategy
from backtest import BacktestEngine, print_report


def run_backtest(min_roe=5.0, min_buy_score=3, require_dividend=True,
                 start="20230101", end="20260605", initial_capital=1_000_000):
    cache = MarketCache("20200101", end)
    strat = V2Strategy(cache,
                       min_roe=min_roe,
                       min_buy_score=min_buy_score,
                       require_dividend=require_dividend)
    engine = BacktestEngine(cache, strat, initial_capital=initial_capital)
    report = engine.run(start, end)
    return report


def print_detailed(report):
    print_report(report)
    df = report["daily_value"]
    trades = report["trades"]

    # 逐年统计
    df["year"] = df["date"].str[:4]
    print("\n--- 逐年收益 ---")
    for year, grp in df.groupby("year"):
        first = grp.iloc[0]["total_value"]
        last = grp.iloc[-1]["total_value"]
        ret = (last - first) / first * 100
        print(f"  {year}: {ret:>6.2f}%")

    # 月度胜率
    if not trades.empty:
        print("\n--- 交易盈亏分布 ---")
        sell = trades[trades["action"] == "SELL"]
        if not sell.empty:
            bins = [-100, -10, -5, 0, 5, 10, 20, 50, 100]
            labels = ["<-10%", "-10%~-5%", "-5%~0%", "0%~5%", "5%~10%", "10%~20%", "20%~50%", ">50%"]
            sell["profit_bin"] = pd.cut(sell["profit_pct"], bins=bins, labels=labels)
            dist = sell["profit_bin"].value_counts().sort_index()
            for k, v in dist.items():
                bar = "█" * v
                print(f"  {k:>8s}: {v:>2d}  {bar}")

        print("\n--- 卖出原因 ---")
        print(sell["reason"].value_counts().to_string())

    # 持仓天数分布
    if not trades.empty:
        buy = trades[trades["action"] == "BUY"][["ts_code", "date"]].rename(columns={"date": "buy_date"})
        sell = trades[trades["action"] == "SELL"][["ts_code", "date", "profit_pct"]].rename(columns={"date": "sell_date"})
        merged = buy.merge(sell, on="ts_code", how="inner")
        if not merged.empty:
            merged["hold_days"] = (pd.to_datetime(merged["sell_date"]) - pd.to_datetime(merged["buy_date"])).dt.days
            print(f"\n--- 平均持有天数: {merged['hold_days'].mean():.1f} 天 ---")
            print(f"  最短: {merged['hold_days'].min()} 天  最长: {merged['hold_days'].max()} 天")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="v2 策略回测")
    parser.add_argument("--min-roe", type=float, default=5.0, help="最小ROE (默认5)")
    parser.add_argument("--min-score", type=int, default=3, help="最小买入打分 (默认3)")
    parser.add_argument("--no-dividend", action="store_true", help="不需要分红")
    parser.add_argument("--start", default="20230101", help="开始日期")
    parser.add_argument("--end", default="20260605", help="结束日期")
    parser.add_argument("--detail", action="store_true", help="展示详细统计")
    args = parser.parse_args()

    report = run_backtest(
        min_roe=args.min_roe,
        min_buy_score=args.min_score,
        require_dividend=not args.no_dividend,
        start=args.start,
        end=args.end,
    )
    if args.detail:
        print_detailed(report)
    else:
        print_report(report)