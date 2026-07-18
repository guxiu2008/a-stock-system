#!/usr/bin/env python3
"""
诊断脚本：检查数据库中股票的同步状态
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text

db_path = "./stock_data.db"
engine = create_engine(f"sqlite:///{db_path}")

ts_code = "000001.SZ"

print("=" * 60)
print(f"诊断股票 {ts_code} 的同步状态")
print("=" * 60)

# 1. 检查 fact_daily_quotes 表中的最新交易日期
print("\n1. 检查行情数据表 (fact_daily_quotes)")
with engine.connect() as conn:
    result = conn.execute(
        text("SELECT MAX(trade_date) FROM fact_daily_quotes WHERE ts_code = :ts_code"),
        {"ts_code": ts_code}
    )
    fact_last_date = result.fetchone()[0]
    print(f"   最新交易日期: {fact_last_date}")
    
    # 显示最近10条数据
    result = conn.execute(
        text("SELECT trade_date, close FROM fact_daily_quotes WHERE ts_code = :ts_code ORDER BY trade_date DESC LIMIT 10"),
        {"ts_code": ts_code}
    )
    print("   最近10条行情数据:")
    for row in result:
        print(f"     {row[0]}: {row[1]}")

# 2. 检查 stock_sync_status 表中的同步状态
print("\n2. 检查同步状态表 (stock_sync_status)")
with engine.connect() as conn:
    result = conn.execute(
        text("SELECT last_sync_date, sync_status, update_time FROM stock_sync_status WHERE ts_code = :ts_code"),
        {"ts_code": ts_code}
    )
    row = result.fetchone()
    if row:
        print(f"   last_sync_date: {row[0]}")
        print(f"   sync_status: {row[1]}")
        print(f"   update_time: {row[2]}")
    else:
        print("   ❌ 该股票在同步状态表中不存在！")

# 3. 检查同步状态表的总记录数
print("\n3. 检查同步状态表总记录数")
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM stock_sync_status"))
    count = result.fetchone()[0]
    print(f"   同步状态表总记录数: {count}")
    
    result = conn.execute(text("SELECT COUNT(DISTINCT ts_code) FROM fact_daily_quotes"))
    stock_count = result.fetchone()[0]
    print(f"   行情数据表中有数据的股票数: {stock_count}")

# 4. 对比检查
print("\n4. 日期对比")
if row:
    sync_last_date = row[0]
    if fact_last_date and sync_last_date:
        print(f"   行情表最新日期: {fact_last_date}")
        print(f"   状态表同步日期: {sync_last_date}")
        if fact_last_date == sync_last_date:
            print("   ✓ 两个日期一致，同步状态正常")
        elif fact_last_date > sync_last_date:
            print("   ⚠️  行情表比状态表新，状态表落后！")
        else:
            print("   ❌ 状态表日期比行情表还新！异常！")
    else:
        print("   数据不完整，无法对比")
else:
    print("   ❌ 状态表无记录，无法对比")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
