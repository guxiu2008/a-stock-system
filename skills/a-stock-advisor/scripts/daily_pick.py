#!/usr/bin/env python3
"""
每日选股：按 mindset.md v2 七步法 + 回测验证过的最优参数

用法:
  python daily_pick.py                  # 默认中期成长（ROE优先，目标30~50%）
  python daily_pick.py --mode swing     # 中期波段（技术+行业轮动，目标15~25%）
  python daily_pick.py --mode short     # 短线波段（2~4周，目标8%）
  python daily_pick.py --fast           # 跳过联网新闻验证
  python daily_pick.py --json           # 输出 JSON
"""
import sys
import os
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.db import check_db_ready, get_conn
from lib.cache import LiveCache
from lib.strategy import StockSelector, get_position_rule
from lib.financials import FinancialAnalyzer
from lib.news_verifier import NewsVerifier


def enrich_and_rerank(result: dict, cache: LiveCache, fast: bool = False, final_limit: int = 5) -> dict:
    candidates = result.get("picks", [])
    result["initial_candidate_count"] = len(candidates)
    result["final_limit"] = final_limit
    result["analysis_flow"] = [
        f"量化策略初筛 {len(candidates)} 只候选",
        "财报质量硬筛和评分",
        "联网新闻/公告/合作方线索验证" if not fast else "快速模式：跳过联网新闻验证",
        f"综合重排输出前 {final_limit} 只",
    ]
    if not candidates:
        return result

    financial_analyzer = FinancialAnalyzer(cache.conn, result["date"])
    news_verifier = None if fast else NewsVerifier()
    reviewed = []
    rejected = []
    for p in candidates:
        financial = financial_analyzer.analyze(p["ts_code"])
        p["financial"] = financial
        if financial.get("metrics", {}).get("roe") is not None:
            p["latest_roe"] = round(financial["metrics"]["roe"], 2)
        if financial.get("hard_reject") or financial.get("score", 0) < 35:
            p["reject_reason"] = "财务硬性风险" if financial.get("hard_reject") else "财务评分低于35"
            rejected.append(p)
            continue
        if news_verifier:
            p["news"] = news_verifier.analyze(p, financial)
        else:
            p["news"] = {
                "available": False,
                "score": 50,
                "confidence": "未联网",
                "summary": "快速模式跳过新闻验证",
                "positive": [],
                "negative": [],
                "risk_flags": ["快速模式未联网"],
                "sources": [],
            }
        p["final_score"] = calc_final_score(p)
        reviewed.append(p)
    if news_verifier:
        news_verifier.save_cache()
    reviewed = sorted(reviewed, key=lambda x: x.get("final_score", 0), reverse=True)
    max_picks = result["position_rule"]["max_picks"]
    for rank, p in enumerate(reviewed[:final_limit], 1):
        p["rank"] = rank
        p["actionable"] = rank <= max_picks
        p["action_note"] = "可操作" if rank <= max_picks else "观察池"
    result["picks"] = reviewed[:final_limit]
    result["reviewed_count"] = len(reviewed)
    result["rejected_count"] = len(rejected)
    result["rejected"] = [
        {"ts_code": p["ts_code"], "name": p["name"], "reason": p.get("reject_reason"), "financial_score": p.get("financial", {}).get("score")}
        for p in rejected[:10]
    ]
    if len(reviewed) < final_limit:
        result["notes"].append(f"财报筛选后仅剩 {len(reviewed)} 只，少于目标 {final_limit} 只")
    return result


def calc_final_score(p: dict) -> float:
    technical = p.get("buy_score", 0) * 12
    momentum = (p.get("ret_20d_pct") or p.get("cum_3d_pct") or 0) * 0.35 + (p.get("ret_60d_pct") or 0) * 0.15
    roe = (p.get("latest_roe") or 0) * 0.4
    financial = p.get("financial", {}).get("score", 0) * 0.35
    news = p.get("news", {}).get("score", 50) * 0.15
    penalties = 0
    if p.get("news", {}).get("confidence") == "低":
        penalties += 5
    if p.get("financial", {}).get("rating") in ("偏弱", "高风险"):
        penalties += 8
    return round(technical + momentum + roe + financial + news - penalties, 2)


def format_text(result: dict) -> str:
    lines = []
    lines.append("=" * 70)
    if result.get("mode") == "growth":
        mode_name = "中期成长"
    elif result.get("mode") == "swing":
        mode_name = "中期波段"
    else:
        mode_name = "短线波段"
    lines.append(f"  每日选股报告  ({result['date']})  [{mode_name}模式]")
    lines.append("=" * 70)

    trend = result["trend"]
    pr = result["position_rule"]
    rsi_signal = result.get("rsi_signal", "正常")
    sentiment_label = result.get("sentiment_label", "⚪ 情绪中性")
    sentiment = result.get("sentiment", 50)
    index_rsi = result.get("index_rsi", 50)
    index_pct = result.get("index_pct", 0)
    trend_change = result.get("trend_change", "不变")
    consecutive_up = result.get("consecutive_up", 0)
    consecutive_down = result.get("consecutive_down", 0)
    is_macd_red = result.get("is_macd_red", False)
    is_macd_gold_cross = result.get("is_macd_gold_cross", False)
    forecast = result.get("forecast", {})
    
    lines.append(f"")
    lines.append(f"【大盘环境】 {trend}  |  市场情绪: {sentiment_label} ({sentiment}/100)")
    lines.append(f"  大盘RSI(6): {index_rsi:.1f}  |  RSI状态: {rsi_signal}  |  今日涨跌: {index_pct:+.2f}%")
    lines.append(f"  仓位规则: 总仓位上限 {pr['max_total']*100:.0f}% | 单票上限 {pr['max_single']*100:.0f}% | 今日最多推荐 {pr['max_picks']} 只")
    
    # 趋势变化提示
    if trend_change == "趋势反转向上":
        lines.append(f"  ✅ 重大信号：大盘已从下跌趋势反转向上，中期趋势走好")
    elif trend_change == "突破向上":
        lines.append(f"  ✅ 信号确认：大盘突破震荡区间，进入上升趋势，可积极布局")
    elif trend_change == "止跌企稳":
        lines.append(f"  🟡 观察信号：大盘已止跌企稳，等待进一步确认方向")
    elif trend_change == "趋势反转向下":
        lines.append(f"  🔴 重大风险：大盘已从上升趋势反转向下，注意控制风险")
    elif trend_change == "破位向下":
        lines.append(f"  🔴 风险信号：大盘破位向下，建议减仓避险")
    elif trend_change == "上升遇阻":
        lines.append(f"  🟡 注意：大盘上升遇阻，短期可能进入震荡整理")
    
    # MACD信号
    if is_macd_gold_cross:
        lines.append(f"  ✅ MACD金叉确认：中期做多信号")
    elif is_macd_red:
        lines.append(f"  ✅ MACD柱状翻红：多头动能增强")
    
    # 连续涨跌提示
    if consecutive_up >= 3:
        lines.append(f"  📈 连续{consecutive_up}日上涨，注意短线获利回吐压力")
    elif consecutive_down >= 3:
        lines.append(f"  📉 连续{consecutive_down}日下跌，超卖后或有反弹机会")
    
    # RSI超买警告
    if rsi_signal == "极度超买":
        lines.append(f"  ⚠️  警告：大盘RSI极度超买({index_rsi:.1f})，短线有回调风险，建议控制仓位，勿追高")
    elif rsi_signal == "超买":
        lines.append(f"  ⚠️  注意：大盘RSI超买({index_rsi:.1f})，注意分批建仓，避免追涨")
    elif rsi_signal == "极度超卖":
        lines.append(f"  💡 提示：大盘RSI极度超卖({index_rsi:.1f})，可考虑左侧分批布局")
    elif rsi_signal == "超卖":
        lines.append(f"  💡 提示：大盘RSI超卖({index_rsi:.1f})，情绪悲观，是逆向布局机会")
    
    # 明日预测
    if forecast:
        direction = forecast.get("direction", "➡️ 震荡")
        confidence = forecast.get("confidence", "中")
        score = forecast.get("score", 50)
        lines.append(f"")
        lines.append(f"【明日预测】 {direction}  (置信度: {confidence}，综合评分: {score}/100)")
        bullish = forecast.get("bullish_signals", 0)
        bearish = forecast.get("bearish_signals", 0)
        if bullish > bearish + 2:
            lines.append(f"  ✅ 多头信号明显，可适度增加仓位")
        elif bullish > bearish:
            lines.append(f"  🟡 多头信号略占优，谨慎偏多")
        elif bearish > bullish + 2:
            lines.append(f"  🔴 空头信号明显，建议降低仓位，勿追高")
        elif bearish > bullish:
            lines.append(f"  🟡 空头信号略占优，谨慎偏空")
        else:
            lines.append(f"  ⚪ 多空信号均衡，保持中性仓位")

    if result["top_industries"]:
        lines.append(f"")
        if result.get("mode") == "growth":
            lines.append(f"【行业基本面评分 TOP 10（ROE+毛利率）】")
            for i, ind in enumerate(result["top_industries"][:10], 1):
                tag = " <-- 选股池" if 1 <= i <= 20 else ""
                lines.append(f"  {i:>2}. {ind['industry']:<10s}  成长分 {ind['growth_score']:>6.2f}  平均ROE {ind['mean_roe']:>5.2f}%  共 {ind['stock_count']:>3d} 只{tag}")
        elif result.get("mode") == "swing":
            lines.append(f"【中期强势行业 TOP 10】")
            for i, ind in enumerate(result["top_industries"][:10], 1):
                tag = " <-- 选股池" if 3 <= i <= 15 else ""
                lines.append(f"  {i:>2}. {ind['industry']:<10s}  强度 {ind['score']:>+6.2f}  20日 {ind.get('ret20', 0):>+6.2f}%  60日 {ind.get('ret60', 0):>+6.2f}%  共 {ind['stock_count']:>3d} 只{tag}")
        else:
            lines.append(f"【近 3 日强势行业 TOP 10】")
            for i, ind in enumerate(result["top_industries"][:10], 1):
                tag = " <-- 选股池" if 3 <= i <= 12 else ""
                lines.append(f"  {i:>2}. {ind['industry']:<10s}  3日均涨 {ind['score']:>+6.2f}%  共 {ind['stock_count']:>3d} 只{tag}")

    if result.get("analysis_flow"):
        lines.append(f"")
        lines.append(f"【分析流程】")
        for step in result["analysis_flow"]:
            lines.append(f"  - {step}")
        lines.append(f"  - 财报筛选淘汰 {result.get('rejected_count', 0)} 只，进入最终评估 {result.get('reviewed_count', len(result.get('picks', [])))} 只")

    if result["notes"]:
        lines.append(f"")
        lines.append(f"【说明】")
        for n in result["notes"]:
            lines.append(f"  - {n}")

    lines.append(f"")
    actionable_count = sum(1 for p in result["picks"] if p.get("actionable"))
    lines.append(f"【今日最终候选】 共 {len(result['picks'])} 只（按综合得分排序，前 {actionable_count} 只为可操作，其余为观察池）")
    if result["picks"]:
        lines.append(f"")
        lines.append(f"  排名  代码        名称      行业    现价    20日涨   ROE%   财务分  技术分  综合分  标签")
        lines.append(f"  " + "-" * 90)
        for rank, p in enumerate(result["picks"], 1):
            code = p['ts_code']
            name = p['name'][:6]
            industry = p.get('industry', '')[:4]
            close = p['close']
            ret20 = p.get('ret_20d_pct', p.get('cum_3d_pct', 0))
            roe = p.get('latest_roe', 0)
            fin_score = p.get('financial', {}).get('score', 0)
            tech_score = p.get('buy_score', 0)
            final = p.get('final_score', 0)
            tag = "⭐可操作" if rank <= actionable_count else " 观察"
            lines.append(f"  {rank:2}.  {code:10}  {name:6}  {industry:4}  {close:6.1f}  {ret20:+6.1f}%  {roe:5.1f}  {fin_score:3.0f}/100  {tech_score:2.0f}/5  {final:5.1f}  {tag}")
    if not result["picks"]:
        lines.append(f"  （无符合条件的标的，建议今日观望）")
    else:
        for i, p in enumerate(result["picks"], 1):
            lines.append(f"")
            status = p.get("action_note", "可操作")
            lines.append(f"  {i}. [{status}] {p['ts_code']}  {p['name']}  [{p['industry']}]")
            if result.get("mode") in ["swing", "growth"]:
                lines.append(f"     当前价: {p['close']:.2f}  |  20日: {p.get('ret_20d_pct'):+.2f}%  |  60日: {p.get('ret_60d_pct'):+.2f}%  |  最新ROE: {p['latest_roe']}")
            else:
                lines.append(f"     当前价: {p['close']:.2f}  |  近3日涨幅: {p['cum_3d_pct']:+.2f}%  |  最新ROE: {p['latest_roe']}")
            if p.get("final_score") is not None:
                lines.append(f"     最终综合分: {p['final_score']:.2f}")
            lines.append(f"     技术面打分: {p['buy_score']}/5")
            s = p["score_details"]
            checks = [
                ("站上MA20", s["price_above_ma20"]),
                ("MACD为正", s["macd_positive"]),
                ("KDJ非超买", s["kdj_in_range"]),
                ("RSI非超买", s["rsi_in_range"]),
                ("未破布林上轨", s["below_boll_upper"]),
            ]
            checks_str = "  ".join(f"{'OK' if v else '--'} {n}" for n, v in checks)
            lines.append(f"     {checks_str}")
            lines.append(f"     [入选理由]")
            lines.append(f"       行业处于策略选股池；技术信号 {p['buy_score']}/5；ROE {p['latest_roe']}；趋势未触发过热过滤")
            if p.get("financial"):
                f = p["financial"]
                lines.append(f"     [财报分析] {f.get('rating')}  {f.get('score')}/100")
                for n in f.get("notes", [])[:5]:
                    lines.append(f"       - {n}")
            if p.get("news"):
                news = p["news"]
                lines.append(f"     [新闻/公告验证] 可信度 {news.get('confidence')}  {news.get('score')}/100")
                lines.append(f"       {news.get('summary')}")
                for n in news.get("positive", [])[:3]:
                    lines.append(f"       + {n}")
                for n in news.get("negative", [])[:3]:
                    lines.append(f"       - {n}")
                for n in news.get("risk_flags", [])[:3]:
                    lines.append(f"       ! {n}")
                sources = news.get("sources", [])[:3]
                if sources:
                    lines.append(f"       来源:")
                    for src in sources:
                        title = src.get("title") or src.get("domain") or "source"
                        lines.append(f"         - {title}: {src.get('url')}")
            lines.append(f"     [操作建议]")
            industry = p.get("industry", "")
            cyclic_industries = ["铜", "小金属", "黄金", "铝", "铅锌", "煤炭", "石油", "化工", "钢铁", "水泥", "造纸"]
            is_cyclic = any(c in industry for c in cyclic_industries)
            if is_cyclic:
                lines.append(f"       ⚠️  周期股提醒：本标的属于{industry}行业，需密切跟踪商品期货价格走势")
            
            risk_reward = p.get("risk_reward_ratio", 0)
            buy_low = p['buy_range'][0]
            buy_high = p['buy_range'][1]
            optimal_buy = (buy_low + buy_high) / 2  # 中间价附近
            
            lines.append(f"       买入区间: {buy_low:.2f} ~ {buy_high:.2f}")
            if p['close'] >= buy_high * 0.98:  # 现价接近区间上限
                lines.append(f"       💡 实操建议：当前价已接近区间上限，建议回踩至 {optimal_buy:.2f} 附近分批买入，勿追高")
            elif p['close'] <= buy_low * 1.02:  # 现价接近区间下限
                lines.append(f"       💡 实操建议：当前价处于区间下沿，可考虑分批建仓")
            
            lines.append(f"       第一目标: {p['target_price']:.2f}  (+{(p['target_price']/p['close']-1)*100:.1f}%)")
            if p.get("second_target_price"):
                lines.append(f"       第二目标: {p['second_target_price']:.2f}  (+{(p['second_target_price']/p['close']-1)*100:.1f}%)")
            lines.append(f"       止损位:   {p['stop_loss']:.2f}  ({(p['stop_loss']/p['close']-1)*100:+.1f}%)")
            
            if risk_reward:
                if risk_reward < 1.2:
                    lines.append(f"       ⚠️  风险收益比: {risk_reward:.2f} : 1（偏低，建议仅在区间下沿介入）")
                elif risk_reward >= 2.0:
                    lines.append(f"       ✅ 风险收益比: {risk_reward:.2f} : 1（优秀，盈亏比合理）")
                else:
                    lines.append(f"       风险收益比: {risk_reward:.2f} : 1")
            
            lines.append(f"       持有周期:  {p['hold_period']}")

    if result.get("rejected"):
        lines.append(f"")
        lines.append("【财报硬筛淘汰样例】")
        for r in result["rejected"][:10]:
            lines.append(f"  - {r['ts_code']} {r['name']}：{r['reason']}，财务分 {r.get('financial_score')}/100")

    lines.append(f"")
    lines.append("=" * 70)
    lines.append("【免责声明】")
    lines.append("  本工具基于历史数据和技术指标，回测年化约 15%，最大回撤可能达 -15%。")
    lines.append("  不保证盈利，请结合自己的判断，并严格执行止损纪律。")
    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="每日选股")
    parser.add_argument("--date", default=None, help="指定日期 (YYYYMMDD)，默认最新交易日")
    parser.add_argument("--mode", choices=["growth", "swing", "short"], default="growth", help="选股模式：growth=3~6个月中期成长(默认，ROE优先，目标30~50%)，swing=1~3个月中期波段，short=2~4周短线")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--fast", action="store_true", help="快速模式：跳过联网新闻验证")
    parser.add_argument("--candidate-limit", type=int, default=50, help="量化初筛候选池数量，默认 50")
    parser.add_argument("--final-limit", type=int, default=8, help="最终输出数量，默认 8")
    parser.add_argument("--db", default=None, help="数据库路径（覆盖 STOCK_DB_PATH）")
    parser.add_argument("--archive", action="store_true", help="自动保存 JSON 和 文本报告到 archive 目录，按 YYYY/MM 分月存放")
    parser.add_argument("--archive-dir", default=None, help="存档目录，默认 skills/a-stock-advisor/archive/，也可通过环境变量 A_STOCK_ARCHIVE_DIR 配置")
    args = parser.parse_args()

    if args.db:
        os.environ["STOCK_DB_PATH"] = args.db

    ok, msg = check_db_ready()
    if not ok:
        print(f"[ERROR] {msg}", file=sys.stderr)
        sys.exit(1)

    cache = LiveCache()
    selector = StockSelector(cache, mode=args.mode)
    result = selector.select(args.date, candidate_limit=args.candidate_limit)
    result = enrich_and_rerank(result, cache, fast=args.fast, final_limit=args.final_limit)
    cache.close()

    if args.archive:
        base_dir = args.archive_dir or os.environ.get("A_STOCK_ARCHIVE_DIR") or str(Path(__file__).resolve().parent.parent / "archive")
        date = result.get("date", "unknown")
        year = date[:4] if len(date) >= 4 else "unknown"
        month = date[4:6] if len(date) >= 6 else "unknown"
        month_dir = Path(base_dir) / year / month
        os.makedirs(month_dir, exist_ok=True)
        mode = result.get("mode", "swing")
        suffix = "_fast" if args.fast else ""
        base_name = f"daily_pick_{date}_{mode}{suffix}"
        json_path = month_dir / f"{base_name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        txt_path = month_dir / f"{base_name}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(format_text(result))
        print(f"[ARCHIVE] Saved to {json_path} and {txt_path}", file=sys.stderr)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(format_text(result))


if __name__ == "__main__":
    main()
