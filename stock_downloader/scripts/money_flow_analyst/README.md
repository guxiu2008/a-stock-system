# 资金流向分析 (Money Flow Analyst)

从 Tushare 获取北向资金、融资融券等资金流向数据，存储到数据库并提供趋势分析功能。

## 功能特性

1. **北向资金数据**
   - 获取每日沪深港通资金流向
   - 支持增量更新，避免重复请求
2. **融资融券数据**
   - 全市场融资融券余额统计
   - 个股融资融券明细
3. **趋势分析**
   - 计算移动平均线
   - 计算变化率
4. **数据持久化**
   - SQLite 数据库存储
   - 日志记录更新状态

## 数据库表结构

### fact_money_flow (资金流向表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| ts_code | TEXT | 股票代码（全市场数据为 NULL） |
| trade_date | TEXT | 交易日期 |
| hsgt_net_amount | REAL | 北向资金合计 |
| hgt_net_amount | REAL | 沪股通 |
| sgt_net_amount | REAL | 深股通 |
| rzye_market | REAL | 全市场融资余额 |
| rqye_market | REAL | 全市场融券余额 |
| rzye | REAL | 个股融资余额 |
| rzmre | REAL | 个股融资买入额 |
| rqye | REAL | 个股融券余额 |
| rqyl | REAL | 个股融券余量 |
| rzrqye | REAL | 个股融资融券余额 |
| margin_ratio | REAL | 担保比例 |
| rz_change_rate | REAL | 融资变化率 |
| update_time | TEXT | 更新时间 |

### money_flow_analyst_log (日志表)

记录数据更新操作日志。

## 快速开始

### 1. 使用 CLI 更新数据

```bash
# 更新所有数据（北向资金 + 全市场融资融券）
python -m scripts.money_flow_analyst.cli --update-all

# 只更新北向资金
python -m scripts.money_flow_analyst.cli --update-hsgt

# 只更新全市场融资融券
python -m scripts.money_flow_analyst.cli --update-margin

# 更新指定日期的个股融资融券明细
python -m scripts.money_flow_analyst.cli --update-stock-margin 20240101
```

### 2. 查询数据

```bash
# 查询指定日期的北向资金
python -m scripts.money_flow_analyst.cli --hsgt-date 20240101

# 查询指定日期的融资融券
python -m scripts.money_flow_analyst.cli --margin-date 20240101

# 查询指定股票的融资融券明细
python -m scripts.money_flow_analyst.cli --stock-margin 000001.SZ
```

### 3. 趋势分析

```bash
# 分析最近30天北向资金趋势
python -m scripts.money_flow_analyst.cli --analyze-hsgt 30

# 分析最近30天融资融券趋势
python -m scripts.money_flow_analyst.cli --analyze-margin 30
```

### 4. 在代码中使用

```python
from scripts.money_flow_analyst import MoneyFlowAnalyst

# 初始化
analyst = MoneyFlowAnalyst("stock_data.db")

# 更新数据
analyst.update_hsgt()
analyst.update_market_margin()

# 查询数据
hsgt_data = analyst.get_hsgt_by_date("20240101")
margin_data = analyst.get_margin_by_date("20240101")

# 趋势分析
hsgt_trend = analyst.analyze_hsgt_trend(days=30)
margin_trend = analyst.analyze_margin_trend(days=30)
```

### 5. 运行示例

```bash
python scripts/money_flow_analyst/example_usage.py
```

## 文件结构

```
scripts/money_flow_analyst/
├── __init__.py         # 模块导出
├── analyst.py          # 主类 MoneyFlowAnalyst
├── database.py         # 数据库操作封装
├── fetcher.py          # Tushare 数据获取
├── cli.py              # 命令行接口
├── example_usage.py    # 使用示例
└── README.md           # 本文档
```

## 数据更新策略 ⏰

| 数据类型 | 更新频率 | 说明 |
|---------|---------|------|
| 北向资金 | 每日收盘后 | 从最后更新日期增量同步 |
| 全市场融资融券 | 每日收盘后 | 从最后更新日期增量同步 |
| 个股融资融券 | 按需或每日 | 数据量大，按需同步 |

### 推荐更新时间
- 北向资金：每日 16:00 - 17:00
- 融资融券：每日 17:00 - 18:00

### 历史数据策略
- **首次下载**: 获取最近 365 天数据
- **增量更新**: 后续只从最后更新日期的下一天开始下载
- **内存优化**: 按日期分批保存，避免大量数据占用内存
- **重复检测**: 保存前检查数据是否已存在，避免重复

## 依赖库

- pandas
- sqlalchemy
- tushare

## 注意事项

1. 确保已在 `config.py` 中配置 Tushare Token
2. 个股融资融券数据量大，默认不包含在 `update_all` 中
3. API 调用间隔 1 秒，避免触发限流