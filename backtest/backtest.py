
#!/usr/bin/env python3
"""
回测引擎 - 基于 MarketCache 优化版
"""
import pandas as pd
import numpy as np

class Position:
    __slots__ = ('ts_code','name','buy_date','buy_price','shares','stop_loss','target_price','industry','trend',
                 'sold','sell_date','sell_price','sell_reason','peak_price')
    def __init__(self, ts_code, name, buy_date, buy_price, shares, stop_loss, target_price, industry, trend):
        for k,v in locals().items():
            if k != 'self': setattr(self, k, v)
        self.sold = False
        self.sell_date = self.sell_price = self.sell_reason = None
        self.peak_price = buy_price

    def profit_pct(self, price):
        return (price - self.buy_price) / self.buy_price * 100


class BacktestEngine:
    def __init__(self, cache, strategy, initial_capital=1_000_000, commission=0.001):
        self.cache = cache
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = []
        self.trade_log = []
        self.daily_values = []
        self.commission = commission
        self._position_limit = 0.90  # 总仓位上限

    def run(self, start_date, end_date):
        dates = [d for d in self.cache.trade_dates if start_date <= d <= end_date]
        total = len(dates)
        print(f"Backtest: {total} days {dates[0]} ~ {dates[-1]}", flush=True)

        for i, date in enumerate(dates):
            if (i+1) % 100 == 0 or i == total - 1:
                print(f"  {i+1}/{total} ({date})", flush=True)

            # 1. 选股 + 建仓（T日选股，T+1开盘买入）
            picks = self.strategy.select_stocks(date)
            trend = self.strategy._get_trend(date)
            _, max_single_ratio, max_picks = self.strategy._get_position(trend)
            active = len([p for p in self.positions if not p.sold])

            # 当前总资产（现金 + 持仓市值），用前一日收盘估算
            pos_value_today = 0
            for p in self.positions:
                if not p.sold:
                    r = self.cache.stock_row(p.ts_code, date)
                    if r is not None and not pd.isna(r["close"]):
                        pos_value_today += p.shares * r["close"]
            total_assets = self.capital + pos_value_today

            for pick in picks:
                if active >= max_picks:
                    break
                # 已用仓位检查
                pos_ratio = pos_value_today / max(total_assets, 1)
                if pos_ratio >= self._position_limit:
                    break

                ts_code = pick["ts_code"]
                # 跳过已持有
                if any(not p.sold and p.ts_code == ts_code for p in self.positions):
                    continue

                buy_price = self.cache.stock_next_open(ts_code, date)
                if buy_price is None or buy_price <= 0:
                    continue

                stop_loss = round(max(buy_price * 0.93, pick["ma20"] * 0.97 if pick.get("ma20") else buy_price * 0.93), 2)
                target_price = buy_price * 1.08

                # 单票预算
                budget = total_assets * max_single_ratio
                # 不能超出现金可用
                budget = min(budget, self.capital * 0.95)
                shares = int(budget / buy_price / 100) * 100
                cost = shares * buy_price * (1 + self.commission)

                if shares < 100 or cost > self.capital:
                    continue

                pos = Position(ts_code, pick["name"], date, buy_price, shares,
                              stop_loss, target_price, pick["industry"], trend)
                self.positions.append(pos)
                self.capital -= cost
                pos_value_today += shares * buy_price
                active += 1
                self.trade_log.append({
                    "date": date, "ts_code": ts_code, "name": pick["name"],
                    "action": "BUY", "price": buy_price, "shares": shares,
                    "cost": cost, "reason": f"score={pick['buy_score']}"
                })

            # 2. 持仓检查
            for pos in self.positions:
                if pos.sold:
                    continue
                row = self.cache.stock_row(pos.ts_code, date)
                if row is None:
                    continue
                close = row["close"]
                if pd.isna(close):
                    continue

                pos.peak_price = max(pos.peak_price, close)
                profit = (close - pos.buy_price) / pos.buy_price

                # 止损
                if close < pos.stop_loss:
                    pos.sold = True
                    pos.sell_date = date
                    pos.sell_price = close
                    pos.sell_reason = "止损"
                    proceeds = pos.shares * close * (1 - self.commission)
                    self.capital += proceeds
                    self.trade_log.append({
                        "date": date, "ts_code": pos.ts_code, "name": pos.name,
                        "action": "SELL", "price": close, "shares": pos.shares,
                        "cost": proceeds, "profit_pct": round(profit * 100, 2),
                        "reason": f"止损" if profit*100 < -5 else f"触及止损({profit*100:.1f}%)"
                    })
                    continue

                # 止盈
                if close >= pos.target_price:
                    pos.sold = True
                    pos.sell_date = date
                    pos.sell_price = close
                    pos.sell_reason = "止盈"
                    proceeds = pos.shares * close * (1 - self.commission)
                    self.capital += proceeds
                    self.trade_log.append({
                        "date": date, "ts_code": pos.ts_code, "name": pos.name,
                        "action": "SELL", "price": close, "shares": pos.shares,
                        "cost": proceeds, "profit_pct": round(profit * 100, 2),
                        "reason": f"止盈({profit*100:.1f}%)"
                    })
                    continue

                # 超时退出（20 个交易日）
                day_diff = dates.index(date) - dates.index(pos.buy_date) if pos.buy_date in dates else 0
                if day_diff >= 20:
                    pos.sold = True
                    pos.sell_date = date
                    pos.sell_price = close
                    pos.sell_reason = "超时"
                    proceeds = pos.shares * close * (1 - self.commission)
                    self.capital += proceeds
                    self.trade_log.append({
                        "date": date, "ts_code": pos.ts_code, "name": pos.name,
                        "action": "SELL", "price": close, "shares": pos.shares,
                        "cost": proceeds, "profit_pct": round(profit * 100, 2),
                        "reason": f"超时{day_diff}天"
                    })

            # 3. 每日估值
            pos_value = 0
            for pos in self.positions:
                if not pos.sold:
                    row = self.cache.stock_row(pos.ts_code, date)
                    if row is not None and not pd.isna(row["close"]):
                        pos_value += pos.shares * row["close"]

            self.daily_values.append({
                "date": date, "capital": self.capital,
                "position_value": pos_value,
                "total_value": self.capital + pos_value,
                "pos_count": len([p for p in self.positions if not p.sold])
            })

        return self._report()

    def _report(self):
        df = pd.DataFrame(self.daily_values)
        trades = pd.DataFrame(self.trade_log)
        if df.empty:
            return {"error": "no data"}

        final = df.iloc[-1]["total_value"]
        total_ret = (final - self.initial_capital) / self.initial_capital * 100
        years = (pd.to_datetime(df.iloc[-1]["date"]) - pd.to_datetime(df.iloc[0]["date"])).days / 365.25
        ann_ret = ((1 + total_ret/100)**(1/years) - 1)*100 if years > 0 else 0

        peak = df["total_value"].cummax()
        dd = (df["total_value"] - peak) / peak * 100
        max_dd = dd.min()
        max_dd_date = df.loc[dd.idxmin(), "date"] if not dd.isna().all() else "?"

        buy_t = trades[trades["action"] == "BUY"]
        sell_t = trades[trades["action"] == "SELL"]
        wins = sell_t[sell_t["profit_pct"] > 0] if not sell_t.empty else pd.DataFrame()
        wr = len(wins)/max(len(sell_t),1)*100

        return {
            "total_return_pct": round(total_ret, 2),
            "annual_return_pct": round(ann_ret, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "max_drawdown_date": max_dd_date,
            "total_trades": len(buy_t),
            "win_rate_pct": round(wr, 2),
            "total_buys": len(buy_t),
            "total_sells": len(sell_t),
            "final_capital": round(final, 2),
            "initial_capital": self.initial_capital,
            "years": round(years, 2),
            "daily_value": df,
            "trades": trades,
        }


def print_report(r):
    print("=" * 60)
    print(f"  v2 策略回测报告  ({r['daily_value'].iloc[0]['date']} ~ {r['daily_value'].iloc[-1]['date']})")
    print("=" * 60)
    print(f"  初始资金: {r['initial_capital']:>10,.0f} 元")
    print(f"  最终资金: {r['final_capital']:>10,.0f} 元")
    print(f"  总收益率:  {r['total_return_pct']:>6.2f}%")
    print(f"  年化收益率: {r['annual_return_pct']:>6.2f}%")
    print(f"  最大回护:  {r['max_drawdown_pct']:>6.2f}% ({r['max_drawdown_date']})")
    print(f"  总交易次数: {r['total_trades']}")
    print(f"  胜率:      {r['win_rate_pct']:>6.2f}%")
    print("=" * 60)
