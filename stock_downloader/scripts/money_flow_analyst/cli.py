#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金流向分析 - 命令行接口
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.money_flow_analyst.analyst import MoneyFlowAnalyst


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='资金流向分析工具')
    parser.add_argument('--db', type=str, default='stock_data.db', help='数据库文件路径')
    parser.add_argument('--update-all', action='store_true', help='更新所有数据')
    parser.add_argument('--update-hsgt', action='store_true', help='更新北向资金数据')
    parser.add_argument('--update-margin', action='store_true', help='更新全市场融资融券数据')
    parser.add_argument('--update-stock-margin', type=str, help='更新指定日期的个股融资融券明细')
    parser.add_argument('--hsgt-date', type=str, help='查询指定日期的北向资金数据')
    parser.add_argument('--margin-date', type=str, help='查询指定日期的融资融券数据')
    parser.add_argument('--stock-margin', type=str, help='查询指定股票的融资融券明细')
    parser.add_argument('--analyze-hsgt', type=int, nargs='?', const=30, help='分析北向资金趋势（指定天数，默认30天）')
    parser.add_argument('--analyze-margin', type=int, nargs='?', const=30, help='分析融资融券趋势（指定天数，默认30天）')
    
    args = parser.parse_args()
    
    analyst = MoneyFlowAnalyst(args.db)
    
    if args.update_all:
        analyst.update_all()
    elif args.update_hsgt:
        analyst.update_hsgt()
    elif args.update_margin:
        analyst.update_market_margin()
    elif args.update_stock_margin:
        analyst.update_stock_margin_by_date(args.update_stock_margin)
    elif args.hsgt_date:
        data = analyst.get_hsgt_by_date(args.hsgt_date)
        print(data if data is not None else "未找到数据")
    elif args.margin_date:
        data = analyst.get_margin_by_date(args.margin_date)
        print(data if data is not None else "未找到数据")
    elif args.stock_margin:
        df = analyst.get_stock_margin(args.stock_margin)
        print(df)
    elif args.analyze_hsgt is not None:
        df = analyst.analyze_hsgt_trend(args.analyze_hsgt)
        print(df)
    elif args.analyze_margin is not None:
        df = analyst.analyze_margin_trend(args.analyze_margin)
        print(df)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()