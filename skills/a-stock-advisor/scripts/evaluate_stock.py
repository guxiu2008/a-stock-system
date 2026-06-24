#!/usr/bin/env python3
"""
单股评估：基于 mindset.md v2 的 6 维度打分，输出 买/观望/卖 建议

用法:
  python evaluate_stock.py 600519.SH
  python evaluate_stock.py 300394.SZ --json
"""
import sys, os, json, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lib.db import check_db_ready, get_conn
from lib.cache import LiveCache
from lib.strategy import get_position_rule
import pandas as pd


def evaluate(cache, ts_code):
    """6 维度评估，返回结构化结果"""
    if ts_code not in cache.universe.index:
        return {"error": f"{ts_code} not in universe (可能是ST/退市/无行业)"}

    meta = cache.universe.loc[ts_code]
    row = cache.stock(ts_code)
    if row is None:
        return {"error": f"{ts_code} 无最新行情数据"}

    history = cache.stock_history(ts_code, n=60)
    trend = cache.trend()
    result = {
        "ts_code": ts_code,
        "name": meta["name"],
        "industry": meta["industry"],
        "date": cache.latest_date,
        "market_trend": trend,
        "close": round(float(row["close"]), 2),
        "scores": {},
        "details": {},
    }

    # 维度 1: 基本面
    fund_score = score_fundamental(cache, ts_code, row, result)
    result["scores"]["fundamental"] = fund_score

    # 维度 2: 技术面
    tech_score = score_technical(row, result)
    result["scores"]["technical"] = tech_score

    # 维度 3: 趋势（个股 3 日和 20 日动量）
    trend_score = score_trend(history, row, result)
    result["scores"]["trend"] = trend_score

    # 维度 4: 量能
    vol_score = score_volume(history, result)
    result["scores"]["volume"] = vol_score

    # 维度 5: 大盘配合
    market_score = score_market(trend, result)
    result["scores"]["market"] = market_score

    # 维度 6: 风险
    risk_score = score_risk(cache, ts_code, row, history, result)
    result["scores"]["risk"] = risk_score

    # 综合
    total = sum(result["scores"].values())
    result["total_score"] = total
    result["max_score"] = 30  # 每个维度满分 5

    # 决策
    result["recommendation"] = make_recommendation(total, result)

    return result


def score_fundamental(cache, ts_code, row, result):
    """基本面打分（0-5）"""
    score = 0
    notes = []

    # 分红
    if cache.has_div.get(ts_code):
        score += 2
        notes.append("[+2] 有分红记录")
    else:
        notes.append("[+0] 无分红记录（高风险壳股嫌疑）")

    # ROE
    roe = cache.latest_roe.get(ts_code)
    if roe is None:
        notes.append("[+0] 无ROE数据")
    elif roe >= 15:
        score += 3
        notes.append(f"[+3] ROE={roe:.2f}% (优秀)")
    elif roe >= 10:
        score += 2
        notes.append(f"[+2] ROE={roe:.2f}% (良好)")
    elif roe >= 5:
        score += 1
        notes.append(f"[+1] ROE={roe:.2f}% (一般)")
    elif roe > 0:
        notes.append(f"[+0] ROE={roe:.2f}% (偏弱)")
    else:
        score -= 1
        notes.append(f"[-1] ROE={roe:.2f}% (亏损)")

    result["details"]["fundamental"] = {"notes": notes, "roe": roe}
    return max(0, min(5, score))


def score_technical(row, result):
    """技术面打分（0-5，复用 mindset.md v2 的 5 维度信号）"""
    score = int(row.get("buy_score", 0)) if not pd.isna(row.get("buy_score")) else 0
    notes = []
    if row.get("s_ma20"): notes.append("[+1] 站上MA20")
    else: notes.append("[+0] 跌破MA20")
    if row.get("s_macd"): notes.append("[+1] MACD为正且向上")
    else: notes.append("[+0] MACD偏弱")
    if row.get("s_kdj"): notes.append("[+1] KDJ在20-80之间")
    else: notes.append("[+0] KDJ超买/超卖")
    if row.get("s_rsi"): notes.append("[+1] RSI在30-70之间")
    else: notes.append("[+0] RSI超买/超卖")
    if row.get("s_boll"): notes.append("[+1] 在布林上轨之下")
    else: notes.append("[+0] 突破布林上轨（过热）")
    result["details"]["technical"] = {"notes": notes, "buy_score": score}
    return score


def score_trend(history, row, result):
    """趋势打分（0-5）"""
    if history.empty or len(history) < 20:
        result["details"]["trend"] = {"notes": ["数据不足"]}
        return 0

    score = 0
    notes = []
    close = float(row["close"])
    ma20 = float(row["ma20"]) if pd.notna(row["ma20"]) else None
    ma60 = float(row["ma60"]) if pd.notna(row.get("ma60")) else None

    # 1) 近 3 日累计涨幅
    cum_3d = row.get("cum_3d_pct")
    if cum_3d is not None and not pd.isna(cum_3d):
        if 0 < cum_3d < 10:
            score += 2
            notes.append(f"[+2] 近3日累计 {cum_3d:+.2f}% (温和上涨)")
        elif cum_3d >= 10:
            score += 1
            notes.append(f"[+1] 近3日累计 {cum_3d:+.2f}% (过热)")
        elif -3 < cum_3d <= 0:
            score += 1
            notes.append(f"[+1] 近3日累计 {cum_3d:+.2f}% (横盘)")
        else:
            notes.append(f"[+0] 近3日累计 {cum_3d:+.2f}% (下跌)")

    # 2) 20 日动量
    if len(history) >= 20:
        close_20d_ago = float(history.iloc[-20]["close"])
        mom_20d = (close - close_20d_ago) / close_20d_ago * 100
        if mom_20d > 5:
            score += 1
            notes.append(f"[+1] 20日动量 {mom_20d:+.2f}%")
        elif mom_20d < -10:
            notes.append(f"[+0] 20日动量 {mom_20d:+.2f}% (大跌)")

    # 3) 均线多头排列
    if ma20 and ma60 and close > ma20 > ma60:
        score += 2
        notes.append(f"[+2] 均线多头排列 (close > MA20 > MA60)")
    elif ma20 and close > ma20:
        score += 1
        notes.append(f"[+1] 站上MA20")

    result["details"]["trend"] = {"notes": notes}
    return max(0, min(5, score))


def score_volume(history, result):
    """量能打分（0-5）"""
    if history.empty or len(history) < 25:
        result["details"]["volume"] = {"notes": ["数据不足"]}
        return 0

    score = 0
    notes = []
    vol_5d = history.tail(5)["vol"].mean()
    vol_20d = history.tail(25).head(20)["vol"].mean()
    if vol_20d > 0:
        ratio = vol_5d / vol_20d
        if 1.2 <= ratio <= 2.5:
            score += 3
            notes.append(f"[+3] 近5日量比 {ratio:.2f} (温和放量)")
        elif 2.5 < ratio <= 4:
            score += 2
            notes.append(f"[+2] 近5日量比 {ratio:.2f} (大幅放量,注意是否拉高出货)")
        elif ratio > 4:
            score += 0
            notes.append(f"[+0] 近5日量比 {ratio:.2f} (异常放量,高风险)")
        elif 0.8 <= ratio < 1.2:
            score += 2
            notes.append(f"[+2] 近5日量比 {ratio:.2f} (持平)")
        else:
            notes.append(f"[+0] 近5日量比 {ratio:.2f} (缩量)")

    # 是否有持续放量
    if len(history) >= 5:
        recent_pct_chg = history.tail(5)["pct_chg"]
        up_days = (recent_pct_chg > 0).sum()
        if up_days >= 3:
            score += 1
            notes.append(f"[+1] 近5日有 {up_days} 天上涨")

    if not notes:
        notes.append("[+0] 量能数据不足")
    result["details"]["volume"] = {"notes": notes}
    return max(0, min(5, score))


def score_market(trend, result):
    """大盘配合打分（0-5）"""
    score = {"上升趋势": 5, "震荡市": 3, "下跌趋势": 1, "unknown": 2}.get(trend, 2)
    notes = [f"[+{score}] 大盘 {trend}"]
    if trend == "下跌趋势":
        notes.append("  下跌市中只做超跌反弹,不追涨")
    result["details"]["market"] = {"notes": notes, "trend": trend}
    return score


def score_risk(cache, ts_code, row, history, result):
    """风险打分（0-5，分数越高越安全）"""
    score = 5
    notes = []

    name = cache.universe.loc[ts_code, "name"] if ts_code in cache.universe.index else ""
    if "ST" in name or "*" in name:
        score -= 3
        notes.append("[-3] ST/退市风险")

    # 上市时间
    list_date = cache.universe.loc[ts_code, "list_date"]
    if list_date and int(cache.latest_date) - int(list_date) < 10000:
        score -= 2
        notes.append("[-2] 上市不足1年 (次新股)")

    # 最近 60 日最大跌幅
    if len(history) >= 60:
        max_close = history["close"].max()
        min_close = history["close"].min()
        current = float(row["close"])
        drawdown = (current - max_close) / max_close * 100
        if drawdown < -20:
            score -= 1
            notes.append(f"[-1] 距60日高点 {drawdown:+.1f}% (大跌)")

    # 单日跌停
    pct_chg = row.get("pct_chg", 0)
    if pct_chg is not None and pct_chg < -9.5:
        score -= 2
        notes.append("[-2] 今日近跌停")

    if not notes:
        notes.append("[+5] 无明显风险信号")
    result["details"]["risk"] = {"notes": notes}
    return max(0, min(5, score))


def make_recommendation(total, result):
    """根据综合打分生成建议"""
    market = result["market_trend"]
    tech = result["scores"]["technical"]
    fund = result["scores"]["fundamental"]
    risk = result["scores"]["risk"]

    # 硬性否决
    if risk <= 1:
        return {
            "action": "回避",
            "reason": "风险评分过低（ST/次新/异常下跌等）",
            "confidence": "高",
        }
    if fund == 0 and tech == 0:
        return {
            "action": "回避",
            "reason": "基本面 + 技术面都没有信号",
            "confidence": "高",
        }
    if market == "下跌趋势" and tech < 3:
        return {
            "action": "观望",
            "reason": "大盘下跌且技术面不够强",
            "confidence": "中",
        }

    # 分段决策
    if total >= 22 and tech >= 4 and risk >= 3:
        return {
            "action": "可买入",
            "reason": f"综合 {total}/30，技术面强势，风险可控",
            "confidence": "高",
            "suggested_position": result.get("position_hint", "建议仓位 10-20%（看大盘）"),
        }
    elif total >= 18 and tech >= 3:
        return {
            "action": "可关注/小仓位试探",
            "reason": f"综合 {total}/30，信号偏正面但不够强",
            "confidence": "中",
            "suggested_position": "建议仓位 5-10%",
        }
    elif total >= 13:
        return {
            "action": "观望",
            "reason": f"综合 {total}/30，信号一般，等更明确机会",
            "confidence": "中",
        }
    else:
        return {
            "action": "回避",
            "reason": f"综合 {total}/30，多个维度不及格",
            "confidence": "高",
        }


def format_text(result):
    if "error" in result:
        return f"[ERROR] {result['error']}"

    lines = []
    lines.append("=" * 70)
    lines.append(f"  单股评估报告  {result['ts_code']}  {result['name']}  [{result['industry']}]")
    lines.append(f"  日期: {result['date']}  |  当前价: {result['close']}  |  大盘: {result['market_trend']}")
    lines.append("=" * 70)

    lines.append("")
    lines.append("【六维度打分 (每维 0-5, 总分 30)】")
    score_labels = {
        "fundamental": "基本面",
        "technical":   "技术面",
        "trend":       "趋势  ",
        "volume":      "量能  ",
        "market":      "大盘  ",
        "risk":        "风险  ",
    }
    for k, label in score_labels.items():
        s = result["scores"][k]
        bar = "*" * s + "." * (5 - s)
        lines.append(f"  {label}  [{bar}]  {s}/5")
    lines.append(f"")
    lines.append(f"  综合得分: {result['total_score']}/30")

    lines.append("")
    lines.append("【各维度细节】")
    for k, label in score_labels.items():
        d = result["details"].get(k, {})
        notes = d.get("notes", [])
        lines.append(f"")
        lines.append(f"  - {label.strip()}:")
        for n in notes:
            lines.append(f"      {n}")

    rec = result["recommendation"]
    lines.append("")
    lines.append("=" * 70)
    lines.append(f"【操作建议】 {rec['action']}  (置信度: {rec['confidence']})")
    lines.append(f"  原因: {rec['reason']}")
    if "suggested_position" in rec:
        lines.append(f"  仓位: {rec['suggested_position']}")

    # 给出参考价位
    close = result["close"]
    lines.append(f"")
    lines.append(f"【参考价位】")
    lines.append(f"  建议买入区间: {close*0.97:.2f} ~ {close*1.00:.2f}")
    lines.append(f"  止损位:       {close*0.93:.2f}  (-7%)")
    lines.append(f"  第一目标:     {close*1.08:.2f}  (+8%)")
    lines.append(f"  第二目标:     {close*1.15:.2f}  (+15%)")
    lines.append("=" * 70)
    lines.append("[免责] 仅供参考，不构成投资建议。请严格执行止损纪律。")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="单股评估")
    parser.add_argument("ts_code", help="股票代码 (如 600519.SH)")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--db", default=None, help="数据库路径")
    args = parser.parse_args()

    if args.db:
        os.environ["STOCK_DB_PATH"] = args.db

    ok, msg = check_db_ready()
    if not ok:
        print(f"[ERROR] {msg}", file=sys.stderr)
        sys.exit(1)

    # 规范化代码（自动加 .SH / .SZ）
    code = args.ts_code.upper().strip()
    if "." not in code:
        if code.startswith("6"):
            code = code + ".SH"
        elif code.startswith(("0", "3")):
            code = code + ".SZ"
        elif code.startswith(("4", "8")):
            code = code + ".BJ"

    cache = LiveCache()
    result = evaluate(cache, code)
    cache.close()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(format_text(result))


if __name__ == "__main__":
    main()
