#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股行情同步工具 - 使用示例
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.market_quota_syncer.syncer import MarketQuotaSyncer


def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("示例1: 基本使用 - 查询历史行情")
    print("=" * 60)
    
    # 初始化行情同步器
    syncer = MarketQuotaSyncer("stock_data.db")
    print("行情同步器初始化完成")
    
    # 尝试查询一只股票的行情（示例用平安银行）
    df = syncer.get_history_prices("000001.SZ")
    if not df.empty:
        print(f"\n000001.SZ 共有 {len(df)} 条行情记录")
        print(df[['trade_date', 'close', 'adj_close', 'vol']].tail(10))
    else:
        print("\n暂无行情数据，请先同步数据")


def example_drawdown_calculation():
    """回撤计算示例"""
    print("\n" + "=" * 60)
    print("示例2: 计算最大回撤")
    print("=" * 60)
    
    syncer = MarketQuotaSyncer("stock_data.db")
    
    df = syncer.get_history_prices("000001.SZ")
    if not df.empty:
        max_drawdown, drawdown_df = syncer.calculate_drawdown("000001.SZ", window=252)
        print(f"000001.SZ 过去252个交易日最大回撤: {max_drawdown:.2%}")
        print("\n最近10个交易日回撤数据:")
        print(drawdown_df.tail(10))
    else:
        print("暂无行情数据")


def example_volume_surge():
    """成交量放量检测示例"""
    print("\n" + "=" * 60)
    print("示例3: 检测成交量放量")
    print("=" * 60)
    
    syncer = MarketQuotaSyncer("stock_data.db")
    
    df = syncer.get_history_prices("000001.SZ")
    if not df.empty and len(df) >= 20:
        is_surge, ratio = syncer.detect_volume_surge("000001.SZ")
        print(f"000001.SZ 成交量放量检测:")
        print(f"  是否放量: {'是' if is_surge else '否'}")
        print(f"  放量倍数: {ratio:.2f}")
    else:
        print("数据不足，无法检测")


def example_query_index():
    """查询指数行情示例"""
    print("\n" + "=" * 60)
    print("示例4: 查询指数行情")
    print("=" * 60)
    
    syncer = MarketQuotaSyncer("stock_data.db")
    
    # 查询上证指数
    df = syncer.get_history_prices("000001.SH", is_index=True)
    if not df.empty:
        print(f"\n上证指数 (000001.SH) 共有 {len(df)} 条行情记录")
        print(df[['trade_date', 'close', 'vol']].tail(10))
    else:
        print("\n暂无指数行情数据")


def example_sync_status():
    """查看同步状态示例"""
    print("\n" + "=" * 60)
    print("示例5: 查看同步状态")
    print("=" * 60)
    
    syncer = MarketQuotaSyncer("stock_data.db")
    
    print("\n指数同步状态:")
    df_indices = syncer.get_all_sync_status(is_index=True)
    print(df_indices)


def example_technical_indicators():
    """技术指标示例"""
    print("\n" + "=" * 60)
    print("示例6: 查看技术指标")
    print("=" * 60)
    
    syncer = MarketQuotaSyncer("stock_data.db")
    
    df = syncer.get_indicators("000001.SZ")
    if not df.empty:
        print(f"\n000001.SZ 共有 {len(df)} 条技术指标记录")
        print(df.tail(10))
    else:
        print("\n暂无技术指标数据，请先同步股票数据")


if __name__ == "__main__":
    print("A股行情同步工具 - 使用示例")
    print("=" * 60)
    
    # 检查是否有数据
    syncer = MarketQuotaSyncer("stock_data.db")
    df = syncer.get_history_prices("000001.SZ")
    
    if df.empty:
        print("数据库中没有行情数据，请先运行:")
        print("  # 同步指数（推荐先运行这个测试）")
        print("  python scripts/market_quota_syncer/cli.py --sync-indices")
        print("\n  # 同步单只股票（测试用）")
        print("  python scripts/market_quota_syncer/cli.py --sync-stock 000001.SZ")
        print("\n  # 同步所有数据（完整数据，耗时较长）")
        print("  python scripts/market_quota_syncer/cli.py --sync-all")
    else:
        # 运行所有示例
        example_basic_usage()
        example_drawdown_calculation()
        example_volume_surge()
        example_query_index()
        example_sync_status()
        example_technical_indicators()
    
    print("\n" + "=" * 60)
    print("示例运行完成!")
    print("=" * 60)