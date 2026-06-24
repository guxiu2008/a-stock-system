#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股息率追踪器 - 命令行接口
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.dividend_yield_tracker.tracker import DividendYieldTracker


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='股息率追踪器管理工具')
    parser.add_argument('--db', type=str, default='stock_data.db', help='数据库文件路径')
    parser.add_argument('--sync-history', type=int, nargs='?', const=10, help='同步历史分红数据（默认10年）')
    parser.add_argument('--sync-latest', action='store_true', help='同步最新分红数据')
    parser.add_argument('--force', action='store_true', help='强制更新（即使数据已存在）')
    parser.add_argument('--cash-cow', type=float, nargs='?', const=0.05, help='获取高股息股票列表（默认最低5%%）')
    parser.add_argument('--check-sustainability', type=str, help='检查指定股票的分红可持续性')
    parser.add_argument('--upcoming', action='store_true', help='获取即将分红的股票列表')
    parser.add_argument('--yield', type=str, dest='calc_yield', help='计算指定股票的静态股息率')
    
    args = parser.parse_args()
    
    tracker = DividendYieldTracker(args.db)
    
    if args.sync_history:
        count = tracker.sync_dividend_history(years=args.sync_history, force_update=args.force)
        print(f"同步完成，共 {count} 条记录")
    elif args.sync_latest:
        count = tracker.sync_latest_dividends()
        print(f"同步完成，共 {count} 条记录")
    elif args.cash_cow:
        df = tracker.get_cash_cow_list(min_yield=args.cash_cow)
        if not df.empty:
            print(f"找到 {len(df)} 只高股息股票（股息率 >= {args.cash_cow*100:.1f}%）：")
            print(df.to_string(index=False))
        else:
            print(f"未找到股息率 >= {args.cash_cow*100:.1f}% 的股票")
    elif args.check_sustainability:
        result = tracker.check_dividend_sustainability(args.check_sustainability)
        print(f"股票 {result['ts_code']} 分红可持续性分析：")
        print(f"  是否可持续: {'是' if result['is_sustainable'] else '否'}")
        print(f"  原因: {result['reason']}")
        print(f"  分红年数: {result['dividend_years']}")
        print(f"  连续分红年数: {result['continuous_years']}")
        print(f"  分红增长: {'是' if result['is_growing'] else '否'}")
    elif args.upcoming:
        df = tracker.get_upcoming_dividends()
        if not df.empty:
            print(f"找到 {len(df)} 只即将分红的股票：")
            print(df[['ts_code', 'ann_date', 'end_date', 'cash_div_tax', 'record_date', 'ex_date', 'div_proc']].to_string(index=False))
        else:
            print("暂无数即将分红的股票")
    elif args.calc_yield:
        dy = tracker.calculate_static_yield(args.calc_yield)
        if dy:
            print(f"股票 {args.calc_yield} 静态股息率: {dy*100:.2f}%")
        else:
            print(f"无法计算股票 {args.calc_yield} 的静态股息率（数据不足）")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()