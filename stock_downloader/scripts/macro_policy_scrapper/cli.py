#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观政策抓取工具 - 命令行接口
"""

import argparse
import sys
from pathlib import Path
import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.macro_policy_scrapper import MacroPolicyScrapper


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='宏观政策抓取工具')
    parser.add_argument('--db', type=str, default='stock_data.db', help='数据库文件路径')
    parser.add_argument('--update-all', action='store_true', help='更新所有数据')
    parser.add_argument('--update-news', action='store_true', help='更新新闻快讯')
    parser.add_argument('--update-eco-cal', action='store_true', help='更新经济日历')
    parser.add_argument('--start-date', type=str, help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end-date', type=str, help='结束日期 (YYYYMMDD)')
    parser.add_argument('--force', action='store_true', help='强制更新（不检查是否已存在）')
    parser.add_argument('--query-keyword', type=str, help='按关键词查询')
    parser.add_argument('--query-date-range', type=str, nargs=2, help='按日期范围查询 (start end)')
    parser.add_argument('--policy-focus', type=int, help='获取当前政策聚焦（天数）')
    parser.add_argument('--check-impact', type=str, help='检查特定行业事件影响')
    parser.add_argument('--safe-period', type=int, help='判断宏观安全期（天数）')
    parser.add_argument('--last-update', type=str, help='查询最后更新时间 (data_type)')
    
    args = parser.parse_args()
    
    scrapper = MacroPolicyScrapper(args.db)
    
    if args.update_all:
        scrapper.update_all(args.start_date, args.end_date, force_update=args.force)
    elif args.update_news:
        scrapper.update_news(args.start_date, args.end_date, force_update=args.force)
    elif args.update_eco_cal:
        scrapper.update_eco_cal(args.start_date, args.end_date, force_update=args.force)
    elif args.query_keyword:
        df = scrapper.get_narratives_by_keyword(args.query_keyword)
        if df.empty:
            print(f"未找到包含关键词 '{args.query_keyword}' 的记录")
        else:
            print(df.to_string())
    elif args.query_date_range:
        start_date, end_date = args.query_date_range
        df = scrapper.get_narratives_by_date_range(start_date, end_date)
        if df.empty:
            print(f"未找到日期范围 {start_date} 到 {end_date} 的记录")
        else:
            print(df.to_string())
    elif args.policy_focus:
        result = scrapper.get_current_policy_focus(days=args.policy_focus)
        print(f"\n{result['message']}\n")
        if result['focus_sectors']:
            print("政策聚焦行业:")
            for sector, count in result['focus_sectors']:
                print(f"  - {sector}: {count} 条")
        if result.get('top_keywords'):
            print("\n热门关键词:")
            for keyword, count in result['top_keywords'][:10]:
                print(f"  - {keyword}: {count} 次")
    elif args.check_impact:
        result = scrapper.check_event_impact(args.check_impact)
        print(f"\n{result['message']}\n")
        if result['events']:
            print("相关事件:")
            for event in result['events']:
                sentiment = f"[{event.get('sentiment', '中性')}]" if event.get('sentiment') else "[中性]"
                importance = f"★{event['importance']}"
                print(f"  {event['date']} {sentiment} {importance} - {event['title']}")
    elif args.safe_period:
        result = scrapper.is_macro_safe_period(days=args.safe_period)
        print(f"\n{result['message']}\n")
        if result['risk_signals']:
            print("风险信号:")
            for signal in result['risk_signals']:
                print(f"  {signal['date']} - {signal['title']}")
        if result['support_signals']:
            print("\n支持信号:")
            for signal in result['support_signals']:
                print(f"  {signal['date']} - {signal['title']}")
    elif args.last_update:
        last_time = scrapper.get_last_update_time(args.last_update)
        if last_time:
            print(f"{args.last_update} 的最后更新时间: {last_time}")
        else:
            print(f"未找到 {args.last_update} 的更新记录")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()