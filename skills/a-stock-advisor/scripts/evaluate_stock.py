#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单股评估入口脚本 - 只做流程编排，不含任何计算逻辑
输出三份 Checklist：短线、波段、中线

用法:
  python evaluate_stock.py 600519.SH          # 默认三合一综合评估
  python evaluate_stock.py 600519.SH --mode short  # 只输出短线

配置方式 (优先级从高到低):
  1. 命令行参数: --output-dir, --db
  2. ../.env 文件配置 (skill 根目录)
  3. 环境变量: CHECKLIST_OUTPUT_DIR, STOCK_DB_PATH
  4. 默认值

环境变量:
  CHECKLIST_OUTPUT_DIR: Checklist 输出目录 (默认: ./output/{date})
  STOCK_DB_PATH: 数据库路径
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 自动加载 skill 根目录的 .env 文件（如果存在）
try:
    from dotenv import load_dotenv
    script_dir = os.path.dirname(os.path.abspath(__file__))
    skill_root = os.path.dirname(script_dir)  # 向上一级到 skill 根目录
    env_path = os.path.join(skill_root, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    # 如果没有 python-dotenv，跳过不影响使用
    pass

from lib.db import check_db_ready
from lib.cache import LiveCache
from lib.stock_evaluator import StockEvaluator
from lib.checklist_output import ChecklistOutput


def main():
    parser = argparse.ArgumentParser(description="单股评估 - 三合一 Checklist 输出")
    parser.add_argument("ts_code", help="股票代码 (如 600519.SH)")
    parser.add_argument("--mode", default="all",
                        choices=["short", "swing", "growth", "all"],
                        help="评估模式: short/swing/growth/all，默认 all")
    parser.add_argument("--output-dir", default=None,
                        help="输出目录（支持 {date} 变量，如 ./output/{date}）")
    parser.add_argument("--db", default=None, help="数据库路径")
    args = parser.parse_args()

    if args.db:
        os.environ["STOCK_DB_PATH"] = args.db

    ok, msg = check_db_ready()
    if not ok:
        print(f"[ERROR] {msg}", file=sys.stderr)
        sys.exit(1)

    # 规范化代码
    code = args.ts_code.upper().strip()
    if "." not in code:
        if code.startswith("6"):
            code = code + ".SH"
        elif code.startswith(("0", "3")):
            code = code + ".SZ"
        elif code.startswith(("4", "8")):
            code = code + ".BJ"

    # 初始化缓存和评估器
    cache = LiveCache()
    evaluator = StockEvaluator(cache)

    # 运行评估
    if args.mode == "all":
        # 三合一模式：跑三份，输出三个文件
        short, swing, growth = evaluator.evaluate_all(code)
        
        output_dir = args.output_dir or os.environ.get("CHECKLIST_OUTPUT_DIR", "./output/{date}")
        files = []
        for container in [short, swing, growth]:
            filepath = ChecklistOutput.save_to_file(container, output_dir=output_dir)
            files.append(filepath)
            print(f"[SAVED] {filepath}")
        
        print()
        print("=" * 70)
        print(f"✅ 三份 Checklist 已生成完毕，共 {len(files)} 个文件")
        print("=" * 70)
    else:
        # 单模式：只跑一份
        method_map = {
            "short": evaluator.build_short_checklist,
            "swing": evaluator.build_swing_checklist,
            "growth": evaluator.build_growth_checklist,
        }
        row = cache.stock(code)
        meta = cache.universe.loc[code]
        name = meta.get("name", code)
        industry = meta.get("industry", "未知")
        
        container = method_map[args.mode](code, name, industry)
        output_dir = args.output_dir or os.environ.get("CHECKLIST_OUTPUT_DIR", "./output/{date}")
        filepath = ChecklistOutput.save_to_file(container, output_dir=output_dir)
        print(f"[SAVED] {filepath}")
    
    cache.close()


if __name__ == "__main__":
    main()
