#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观政策抓取工具 - 使用示例
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.macro_policy_scrapper import MacroPolicyScrapper


def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("示例1: 基本使用")
    print("=" * 60)
    
    # 初始化宏观政策抓取器
    scrapper = MacroPolicyScrapper("stock_data.db")
    print("宏观政策抓取器初始化完成")
    
    # 查询最近的宏观政策叙事（只显示前5条）
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    
    df = scrapper.get_narratives_by_date_range(start_date, end_date)
    if not df.empty:
        print(f"\n最近30天共有 {len(df)} 条宏观政策叙事")
        print(df[['event_date', 'source', 'title', 'importance']].head())
    else:
        print("\n暂无数据，请先运行更新命令")


def example_policy_focus():
    """获取政策聚焦示例"""
    print("\n" + "=" * 60)
    print("示例2: 获取当前政策聚焦")
    print("=" * 60)
    
    scrapper = MacroPolicyScrapper("stock_data.db")
    result = scrapper.get_current_policy_focus(days=30)
    
    print(f"\n{result['message']}\n")
    
    if result['focus_sectors']:
        print("政策聚焦行业:")
        for i, (sector, count) in enumerate(result['focus_sectors'], 1):
            print(f"  {i}. {sector}: {count} 条")
    
    if result.get('top_keywords'):
        print("\n热门关键词:")
        for i, (keyword, count) in enumerate(result['top_keywords'][:10], 1):
            print(f"  {i}. {keyword}: {count} 次")


def example_check_impact():
    """检查行业事件影响示例"""
    print("\n" + "=" * 60)
    print("示例3: 检查特定行业事件影响")
    print("=" * 60)
    
    scrapper = MacroPolicyScrapper("stock_data.db")
    
    # 检查几个重要行业
    sectors = ['人工智能', '半导体', '新能源', '数字经济']
    
    for sector in sectors:
        result = scrapper.check_event_impact(sector, days=30)
        print(f"\n--- {sector} ---")
        print(result['message'])
        if result['events']:
            print(f"  最近事件:")
            for event in result['events'][:3]:  # 只显示最近3条
                sentiment = f"[{event.get('sentiment', '中性')}]" if event.get('sentiment') else "[中性]"
                print(f"    {event['date']} {sentiment} - {event['title'][:40]}...")


def example_safe_period():
    """判断宏观安全期示例"""
    print("\n" + "=" * 60)
    print("示例4: 判断宏观安全期")
    print("=" * 60)
    
    scrapper = MacroPolicyScrapper("stock_data.db")
    result = scrapper.is_macro_safe_period(days=14)
    
    print(f"\n{result['message']}\n")
    
    if result['risk_signals']:
        print("风险信号:")
        for signal in result['risk_signals']:
            print(f"  {signal['date']} - {signal['title']}")
    
    if result['support_signals']:
        print("\n支持信号:")
        for signal in result['support_signals']:
            print(f"  {signal['date']} - {signal['title']}")


def example_update():
    """更新数据示例（注释掉，避免误运行）"""
    print("\n" + "=" * 60)
    print("示例5: 更新数据（需手动执行）")
    print("=" * 60)
    print("\n如需更新数据，请执行以下命令:")
    print("  python -m scripts.macro_policy_scrapper.cli --update-all")
    print("\n或者单独更新特定数据:")
    print("  python -m scripts.macro_policy_scrapper.cli --update-news")
    print("  python -m scripts.macro_policy_scrapper.cli --update-eco-cal")


def example_last_update_time():
    """查询最后更新时间示例"""
    print("\n" + "=" * 60)
    print("示例6: 查询数据更新时间")
    print("=" * 60)
    
    scrapper = MacroPolicyScrapper("stock_data.db")
    
    data_types = ['news', 'eco_cal']
    
    for data_type in data_types:
        last_update = scrapper.get_last_update_time(data_type)
        print(f"{data_type}: {last_update or '从未更新'}")


if __name__ == "__main__":
    print("宏观政策抓取工具 - 使用示例")
    print("=" * 60)
    
    # 先检查数据库是否有数据
    scrapper = MacroPolicyScrapper("stock_data.db")
    from datetime import datetime, timedelta
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
    df = scrapper.get_narratives_by_date_range(start_date, end_date)
    
    if df.empty:
        print("数据库中没有数据，请先运行:")
        print("python -m scripts.macro_policy_scrapper.cli --update-all")
    else:
        # 运行所有示例
        example_basic_usage()
        example_policy_focus()
        example_check_impact()
        example_safe_period()
        example_last_update_time()
    
    example_update()
    
    print("\n" + "=" * 60)
    print("示例运行完成!")
    print("=" * 60)