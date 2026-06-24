#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股息率追踪器使用示例
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.dividend_yield_tracker.tracker import DividendYieldTracker


def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("示例1: 基本使用")
    print("=" * 60)
    
    # 初始化股息率追踪器
    tracker = DividendYieldTracker("stock_data.db")
    print("股息率追踪器初始化完成")
    
    # 查询所有分红数据（只显示前5条）
    df = tracker.db.get_all_dividends()
    if not df.empty:
        print(f"\n共有 {len(df)} 条分红记录")
        print(df[['ts_code', 'end_date', 'cash_div_tax', 'div_proc']].head())
    else:
        print("\n暂无分红数据")


def example_cash_cow_list():
    """获取高股息股票列表示例"""
    print("\n" + "=" * 60)
    print("示例2: 获取高股息股票列表（现金牛）")
    print("=" * 60)
    
    tracker = DividendYieldTracker("stock_data.db")
    
    # 获取股息率大于5%的股票
    df = tracker.get_cash_cow_list(min_yield=0.05)
    
    if not df.empty:
        print(f"找到 {len(df)} 只高股息股票（股息率 >= 5%）")
        print(df[['ts_code', 'static_yield', 'cash_div_tax', 'is_sustainable', 'continuous_years']].head(10))
    else:
        print("未找到符合条件的高股息股票")


def example_check_sustainability():
    """检查分红可持续性示例"""
    print("\n" + "=" * 60)
    print("示例3: 检查股票分红可持续性")
    print("=" * 60)
    
    tracker = DividendYieldTracker("stock_data.db")
    
    # 先找一只有分红数据的股票
    df = tracker.db.get_all_dividends()
    if not df.empty:
        sample_ts_code = df['ts_code'].iloc[0]
        print(f"检查股票: {sample_ts_code}")
        
        result = tracker.check_dividend_sustainability(sample_ts_code)
        print(f"  是否可持续: {'是' if result['is_sustainable'] else '否'}")
        print(f"  原因: {result['reason']}")
        print(f"  分红年数: {result['dividend_years']}")
        print(f"  连续分红年数: {result['continuous_years']}")
        print(f"  分红增长: {'是' if result['is_growing'] else '否'}")
    else:
        print("暂无分红数据可供分析")


def example_calculate_yield():
    """计算静态股息率示例"""
    print("\n" + "=" * 60)
    print("示例4: 计算静态股息率")
    print("=" * 60)
    
    tracker = DividendYieldTracker("stock_data.db")
    
    # 先找一只有分红数据的股票
    df = tracker.db.get_all_dividends()
    if not df.empty:
        sample_ts_code = df['ts_code'].iloc[0]
        print(f"计算股票: {sample_ts_code}")
        
        dy = tracker.calculate_static_yield(sample_ts_code)
        if dy:
            print(f"  静态股息率: {dy*100:.2f}%")
        else:
            print(f"  无法计算（数据不足）")
    else:
        print("暂无分红数据可供计算")


def example_upcoming_dividends():
    """获取即将分红的股票列表示例"""
    print("\n" + "=" * 60)
    print("示例5: 获取即将分红的股票")
    print("=" * 60)
    
    tracker = DividendYieldTracker("stock_data.db")
    
    df = tracker.get_upcoming_dividends()
    if not df.empty:
        print(f"找到 {len(df)} 只即将分红的股票")
        print(df[['ts_code', 'ann_date', 'end_date', 'cash_div_tax', 'record_date', 'ex_date']].head(10))
    else:
        print("暂无即将分红的股票")


if __name__ == "__main__":
    print("股息率追踪器 - 使用示例")
    print("=" * 60)
    
    # 先检查数据库是否有数据
    tracker = DividendYieldTracker("stock_data.db")
    df = tracker.db.get_all_dividends()
    
    if len(df) == 0:
        print("数据库中没有分红数据，请先运行:")
        print("python -m scripts.dividend_yield_tracker.cli --sync-history 10")
    else:
        # 运行所有示例
        example_basic_usage()
        example_cash_cow_list()
        example_check_sustainability()
        example_calculate_yield()
        example_upcoming_dividends()
    
    print("\n" + "=" * 60)
    print("示例运行完成!")
    print("=" * 60)