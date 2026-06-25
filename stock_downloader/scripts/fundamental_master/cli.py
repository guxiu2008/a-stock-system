#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务护城河数据工具 - 命令行接口
"""

import argparse
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.fundamental_master.master import FundamentalMaster


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='财务护城河数据工具')
    parser.add_argument('--db', type=str, default='stock_data.db', help='数据库文件路径')
    
    # 更新数据相关
    parser.add_argument('--update', action='store_true', help='更新财务数据（批量优化模式）')
    parser.add_argument('--ts-code', type=str, help='指定股票代码更新')
    parser.add_argument('--period', type=str, help='指定报告期 (如 20231231)')
    parser.add_argument('--start-date', type=str, help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end-date', type=str, help='结束日期 (YYYYMMDD)')
    parser.add_argument('--update-10y', action='store_true', help='更新过去10年数据')
    
    # 查询相关
    parser.add_argument('--query', type=str, help='查询财务报告')
    parser.add_argument('--health-score', type=str, help='获取财务健康评分')
    parser.add_argument('--find-moat', action='store_true', help='筛选护城河股票')
    parser.add_argument('--min-roe', type=float, default=15, help='最低ROE要求 (默认15)')
    parser.add_argument('--detect-flags', type=str, help='检测财务预警信号')

    # 主营业务构成相关
    parser.add_argument('--update-segments', action='store_true', help='更新主营业务构成数据')
    parser.add_argument('--query-segments', type=str, help='查询主营业务构成')
    parser.add_argument('--analyze-structure', type=str, help='分析收入结构质量')
    parser.add_argument('--bz-type', type=str, help='主营业务类型过滤 (P/I/R)')
    
    args = parser.parse_args()
    
    master = FundamentalMaster(args.db)
    
    if args.update:
        master.update_financial_data(
            ts_code=args.ts_code,
            start_date=args.start_date,
            end_date=args.end_date,
            period=args.period
        )
    elif args.update_10y:
        master.update_last_10_years(ts_code=args.ts_code)
    elif args.query:
        df = master.get_financial_reports(ts_code=args.query)
        print(df)
    elif args.health_score:
        result = master.get_financial_health_score(args.health_score)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.find_moat:
        result = master.find_moat_stocks(min_roe=args.min_roe)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.detect_flags:
        result = master.detect_accounting_red_flags(args.detect_flags)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.update_segments:
        master.update_revenue_segments(ts_code=args.ts_code, period=args.period)
    elif args.query_segments:
        df = master.get_revenue_segments(ts_code=args.query_segments, end_date=args.period,
                                         bz_type=args.bz_type)
        print(df)
    elif args.analyze_structure:
        result = master.analyze_revenue_structure(args.analyze_structure)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 默认显示帮助
        parser.print_help()


if __name__ == "__main__":
    main()