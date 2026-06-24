#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金流向分析使用示例
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.money_flow_analyst.analyst import MoneyFlowAnalyst


def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("示例1: 基本使用 - 查询最新北向资金数据")
    print("=" * 60)
    
    analyst = MoneyFlowAnalyst("stock_data.db")
    print("资金流向分析初始化完成")
    
    # 查询北向资金历史数据
    df_hsgt = analyst.db.get_hsgt_history()
    if len(df_hsgt) > 0:
        print(f"\n共有 {len(df_hsgt)} 条北向资金记录")
        print(df_hsgt.tail())
    else:
        print("\n暂无北向资金数据，请先运行更新")


def example_query_margin():
    """查询融资融券数据示例"""
    print("\n" + "=" * 60)
    print("示例2: 查询融资融券数据")
    print("=" * 60)
    
    analyst = MoneyFlowAnalyst("stock_data.db")
    
    df_margin = analyst.db.get_margin_history()
    if len(df_margin) > 0:
        print(f"共有 {len(df_margin)} 条融资融券记录")
        print(df_margin.tail())
    else:
        print("暂无融资融券数据，请先运行更新")


def example_analyze_trend():
    """趋势分析示例"""
    print("\n" + "=" * 60)
    print("示例3: 北向资金趋势分析")
    print("=" * 60)
    
    analyst = MoneyFlowAnalyst("stock_data.db")
    
    df_trend = analyst.analyze_hsgt_trend(days=30)
    if len(df_trend) > 0:
        print("北向资金趋势分析结果:")
        print(df_trend[['trade_date', 'hsgt_net_amount', 'hsgt_ma5', 'hsgt_ma20']].tail(10))
    else:
        print("数据不足，无法分析趋势")


def example_check_update_time():
    """查询更新时间示例"""
    print("\n" + "=" * 60)
    print("示例4: 查询数据更新时间")
    print("=" * 60)
    
    analyst = MoneyFlowAnalyst("stock_data.db")
    
    last_hsgt = analyst.get_last_update_time('update')
    last_hsgt_date = analyst.db.get_last_hsgt_date()
    last_margin_date = analyst.db.get_last_margin_date()
    
    print(f"最后操作记录时间: {last_hsgt or '从未更新'}")
    print(f"北向资金最新日期: {last_hsgt_date or '无数据'}")
    print(f"融资融券最新日期: {last_margin_date or '无数据'}")


if __name__ == "__main__":
    print("资金流向分析 - 使用示例")
    print("=" * 60)
    
    analyst = MoneyFlowAnalyst("stock_data.db")
    
    # 检查是否有数据
    df_hsgt = analyst.db.get_hsgt_history()
    df_margin = analyst.db.get_margin_history()
    
    if len(df_hsgt) == 0 and len(df_margin) == 0:
        print("数据库中没有资金流向数据，请先运行:")
        print("python -m scripts.money_flow_analyst.cli --update-all")
    else:
        example_basic_usage()
        example_query_margin()
        example_analyze_trend()
        example_check_update_time()
    
    print("\n" + "=" * 60)
    print("示例运行完成!")
    print("=" * 60)