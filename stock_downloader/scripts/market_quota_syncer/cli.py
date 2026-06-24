#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股行情同步工具 - 命令行接口
参考 main.py 实现方式
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.market_quota_syncer.syncer import MarketQuotaSyncer


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='A股行情同步工具 - 增量同步（优化版）')
    parser.add_argument('--db', type=str, default='stock_data.db', help='数据库文件路径')
    parser.add_argument('--sync-all', action='store_true', help='同步所有行情数据（股票+指数）')
    parser.add_argument('--sync-stocks', action='store_true', help='同步所有股票行情')
    parser.add_argument('--sync-stock', type=str, help='同步指定股票行情')
    parser.add_argument('--sync-indices', action='store_true', help='同步所有指数行情')
    parser.add_argument('--sync-index', type=str, help='同步指定指数行情')
    parser.add_argument('--max-stocks', type=int, default=None, help='最多同步股票数量（用于测试）')
    parser.add_argument('--delay', type=float, default=0.3, help='请求间隔时间(秒)')
    # 新增优化选项
    parser.add_argument('--no-batch', action='store_true', help='不使用批量模式（使用逐只股票模式）')
    parser.add_argument('--batch-size', type=int, default=100, help='批量模式下每批的股票数（默认 100）')
    parser.add_argument('--no-calc-indicators', action='store_true', help='不计算技术指标（默认会计算，对股票和指数都生效）')
    parser.add_argument('--calc-index-indicators', action='store_true', help='单独回填所有指数的技术指标（不获取新数据）')
    # 查询选项
    parser.add_argument('--query-prices', type=str, help='查询历史行情')
    parser.add_argument('--query-indicators', type=str, help='查询技术指标')
    parser.add_argument('--query-drawdown', type=str, help='计算最大回撤')
    parser.add_argument('--drawdown-window', type=int, default=252, help='回撤窗口（交易日数）')
    parser.add_argument('--query-volume', type=str, help='检测成交量放量')
    parser.add_argument('--status', action='store_true', help='查看同步状态')
    parser.add_argument('--calc-indicators-all', action='store_true', help='单独计算所有股票的技术指标（不获取新数据）')
    
    args = parser.parse_args()
    
    syncer = MarketQuotaSyncer(args.db)
    
    use_batch = not args.no_batch
    
    if args.calc_index_indicators:
        # 仅回填指数指标：复用 calculate_indicators_all 的指数分支，但跳过股票
        syncer.calculate_indicators_all(max_stocks=0, stock_list=[], include_indices=True)
    elif args.calc_indicators_all:
        syncer.calculate_indicators_all(args.max_stocks, include_indices=True)
    elif args.sync_all:
        syncer.sync_all(args.max_stocks, args.delay, use_batch=use_batch, 
                       batch_size=args.batch_size, calculate_indicators=not args.no_calc_indicators)
    elif args.sync_stocks:
        if use_batch:
            syncer.sync_all_stocks_batch(args.max_stocks, args.delay, 
                                        batch_size=args.batch_size, 
                                        calculate_indicators=not args.no_calc_indicators)
        else:
            syncer.sync_all_stocks(args.max_stocks, args.delay)
    elif args.sync_stock:
        syncer.sync_single_stock(args.sync_stock, args.delay)
    elif args.sync_indices:
        syncer.sync_all_indices(args.delay, calculate_indicators=not args.no_calc_indicators)
    elif args.sync_index:
        syncer.sync_single_index(args.sync_index, calculate_indicators=not args.no_calc_indicators)
    elif args.query_prices:
        df = syncer.get_history_prices(args.query_prices)
        print(df)
    elif args.query_indicators:
        df = syncer.get_indicators(args.query_indicators)
        print(df)
    elif args.query_drawdown:
        max_drawdown, df = syncer.calculate_drawdown(args.query_drawdown, args.drawdown_window)
        print(f"最大回撤: {max_drawdown:.2%}")
        print(df.tail(10))
    elif args.query_volume:
        is_surge, ratio = syncer.detect_volume_surge(args.query_volume)
        print(f"成交量放量: {'是' if is_surge else '否'}, 放量倍数: {ratio:.2f}")
    elif args.status:
        print("股票同步状态:")
        df_stocks = syncer.get_all_sync_status(is_index=False)
        print(df_stocks)
        print("\n指数同步状态:")
        df_indices = syncer.get_all_sync_status(is_index=True)
        print(df_indices)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()