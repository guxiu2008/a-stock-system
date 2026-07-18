#!/usr/bin/env python3
"""
查询财务相关表的数据量
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text

db_path = "./stock_data.db"
engine = create_engine(f"sqlite:///{db_path}")

print("=" * 70)
print("财务相关表数据量统计")
print("=" * 70)

# 1. 财务报告表
print("\n📊 1. fact_financial_reports (财务报告表)")
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM fact_financial_reports"))
    total = result.fetchone()[0]
    print(f"   总记录数: {total:,}")
    
    result = conn.execute(text("SELECT COUNT(DISTINCT ts_code) FROM fact_financial_reports"))
    stock_count = result.fetchone()[0]
    print(f"   涉及股票数: {stock_count:,}")
    
    result = conn.execute(text("SELECT end_date, COUNT(*) as cnt FROM fact_financial_reports GROUP BY end_date ORDER BY end_date DESC LIMIT 10"))
    print("   按报告期统计 (最新10期):")
    for row in result:
        print(f"     {row[0]}: {row[1]:,} 条")

# 2. 主营业务构成表
print("\n📊 2. fact_revenue_segments (主营业务构成表)")
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM fact_revenue_segments"))
    total = result.fetchone()[0]
    print(f"   总记录数: {total:,}")
    
    result = conn.execute(text("SELECT COUNT(DISTINCT ts_code) FROM fact_revenue_segments"))
    stock_count = result.fetchone()[0]
    print(f"   涉及股票数: {stock_count:,}")
    
    result = conn.execute(text("SELECT end_date, COUNT(*) as cnt FROM fact_revenue_segments GROUP BY end_date ORDER BY end_date DESC LIMIT 10"))
    print("   按报告期统计 (最新10期):")
    for row in result:
        print(f"     {row[0]}: {row[1]:,} 条")

# 3. 查看单只股票的详细数据
print("\n" + "=" * 70)
print("示例: 查看 000001.SZ 平安银行 的财务数据")
print("=" * 70)

ts_code = "000001.SZ"
with engine.connect() as conn:
    result = conn.execute(
        text("SELECT end_date, COUNT(*) FROM fact_financial_reports WHERE ts_code = :ts_code GROUP BY end_date ORDER BY end_date DESC"),
        {"ts_code": ts_code}
    )
    print(f"\n{ts_code} 各期财务报告记录数:")
    for row in result:
        print(f"   {row[0]}: {row[1]} 条")

print("\n" + "=" * 70)
print("统计完成")
print("=" * 70)
