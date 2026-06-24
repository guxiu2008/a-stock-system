#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产注册表使用示例
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.asset_registry.registry import AssetRegistry


def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("示例1: 基本使用")
    print("=" * 60)
    
    # 初始化资产注册表
    registry = AssetRegistry("stock_data.db")
    print("资产注册表初始化完成")
    
    # 查询所有股票信息（只显示前5条）
    df = registry.get_stock_info()
    print(f"\n共有 {len(df)} 只股票")
    print(df[['ts_code', 'name', 'industry', 'market']].head())


def example_query_by_industry():
    """按行业查询示例"""
    print("\n" + "=" * 60)
    print("示例2: 按行业查询股票")
    print("=" * 60)
    
    registry = AssetRegistry("stock_data.db")
    
    # 获取所有股票信息来查看有哪些行业
    df = registry.get_stock_info()
    if len(df) > 0:
        # 获取第一个行业
        first_industry = df['industry'].dropna().iloc[0] if not df['industry'].dropna().empty else None
        if first_industry:
            print(f"查询行业: {first_industry}")
            industry_stocks = registry.get_stocks_by_industry(first_industry)
            print(f"该行业共有 {len(industry_stocks)} 只股票")
            print(industry_stocks[['ts_code', 'name']].head())


def example_check_trading_day():
    """查询交易日示例"""
    print("\n" + "=" * 60)
    print("示例3: 查询交易日")
    print("=" * 60)
    
    registry = AssetRegistry("stock_data.db")
    
    # 查询今天是否是交易日
    from datetime import datetime
    today = datetime.now().strftime('%Y%m%d')
    is_open = registry.is_trading_day(today)
    print(f"今天 ({today}) 是否是交易日: {is_open}")


def example_check_update_time():
    """查询更新时间示例"""
    print("\n" + "=" * 60)
    print("示例4: 查询数据更新时间")
    print("=" * 60)
    
    registry = AssetRegistry("stock_data.db")
    
    data_types = ['stock_basic', 'industry_classify', 'trade_calendar']
    
    for data_type in data_types:
        last_update = registry.get_last_update_time(data_type)
        print(f"{data_type}: {last_update or '从未更新'}")


if __name__ == "__main__":
    print("资产注册表 - 使用示例")
    print("=" * 60)
    
    # 先检查数据库是否有数据
    registry = AssetRegistry("stock_data.db")
    df = registry.get_stock_info()
    
    if len(df) == 0:
        print("数据库中没有数据，请先运行:")
        print("python -m scripts.asset_registry.cli --update-all")
    else:
        # 运行所有示例
        example_basic_usage()
        example_query_by_industry()
        example_check_trading_day()
        example_check_update_time()
    
    print("\n" + "=" * 60)
    print("示例运行完成!")
    print("=" * 60)