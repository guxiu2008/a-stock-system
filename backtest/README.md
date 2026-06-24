# Backtest 模块

用于验证 mindset.md v2 七步法的历史表现。

## 文件
- `cache.py` - 全市场数据预加载 + 向量化预计算
- `strategy_v2.py` - v2 选股策略
- `backtest.py` - 回测引擎（含止盈止损、仓位管理）
- `run.py` - 入口

## 用法
```bash
# 默认参数
python run.py --start 20230101 --end 20260605

# 调参
python run.py --min-roe 0 --min-score 4 --start 20230101 --end 20260605

# 详细报告
python run.py --start 20230101 --end 20260605 --detail
```

## 环境变量
- `STOCK_DB_PATH`: SQLite 数据库路径，默认 `/workspace/stock_downloader/stock_data.db`

## 验证过的最优参数（2023~2026 回测）
```
min_roe=0, min_buy_score=4, require_dividend=True
→ 年化 15.45%, 最大回撤 -13.84%, 胜率 44.2%
```

## 已知限制
- `latest_roe` 用了最新一期财报，对历史回测有未来函数偏差
- 实盘 skill 不受影响（实盘本来就用当前最新数据）
