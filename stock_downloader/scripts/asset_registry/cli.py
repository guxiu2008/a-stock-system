#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产注册表 - 命令行接口
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.asset_registry.registry import AssetRegistry


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='资产注册表管理工具')
    parser.add_argument('--db', type=str, default='stock_data.db', help='数据库文件路径')
    parser.add_argument('--update-all', action='store_true', help='更新所有数据')
    parser.add_argument('--update-stock', action='store_true', help='更新股票基础信息')
    parser.add_argument('--update-industry', action='store_true', help='更新行业分类')
    parser.add_argument('--update-concept', action='store_true', help='更新概念分类')
    parser.add_argument('--update-calendar', action='store_true', help='更新交易日历')
    parser.add_argument('--query-stock', type=str, help='查询股票信息')
    parser.add_argument('--query-industry', type=str, help='查询行业股票')
    parser.add_argument('--query-concept', type=str, help='查询概念股票')
    parser.add_argument('--query-concepts', type=str, help='查询某股票所属概念')
    
    args = parser.parse_args()
    
    registry = AssetRegistry(args.db)
    
    if args.update_all:
        registry.update_all()
    elif args.update_stock:
        registry.update_stock_basic()
    elif args.update_industry:
        registry.update_industry_classify()
    elif args.update_concept:
        registry.update_concept_classify()
    elif args.update_calendar:
        registry.update_trade_calendar()
    elif args.query_stock:
        df = registry.get_stock_info(ts_code=args.query_stock)
        print(df)
    elif args.query_industry:
        df = registry.get_stocks_by_industry(args.query_industry)
        print(df)
    elif args.query_concept:
        df = registry.get_stocks_by_concept(args.query_concept)
        print(df)
    elif args.query_concepts:
        df = registry.get_concepts_by_stock(args.query_concepts)
        print(df)
    else:
        # 默认显示帮助
        parser.print_help()


if __name__ == "__main__":
    main()