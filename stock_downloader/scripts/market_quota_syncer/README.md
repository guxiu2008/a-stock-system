# A股行情同步工具 (Market Quota Syncer)

这是 Agent 系统的"行情数据底座"，负责同步全量 A 股及主流指数的历史行情数据，包含前复权价格计算，**仅支持增量同步**，同步时自动计算技术指标。

> 参考 main.py 和 src/downloader.py 的实现方式

## 项目结构

```
scripts/market_quota_syncer/
├── __init__.py       # 模块初始化文件
├── database.py       # 数据库管理模块
├── fetcher.py        # 数据获取模块
├── indicators.py     # 技术指标计算模块（新增）
├── syncer.py         # 主同步器类
├── cli.py            # 命令行接口
├── example_usage.py  # 使用示例
├── requirement.txt   # 需求文档
└── README.md         # 使用说明文档
```

## 功能特性

1. **个股行情同步**：同步全量 A 股日线行情，自动计算前复权价格
2. **指数行情同步**：同步上证指数、深证成指、沪深300、创业板指、中证1000
3. **复权因子处理**：自动获取复权因子并计算前复权价格（adj_open/adj_high/adj_low/adj_close）
4. **增量同步**：自动检测最后更新日期，仅同步缺失数据（参考 main.py 实现）
5. **技术指标计算**：同步股票行情时自动计算并保存所有技术指标（MA、MACD、KDJ、RSI、BOLL）
6. **限流保护**：内置 API 调用间隔，避免触发 Tushare 限流
7. **Agent 接口**：提供历史行情查询、最大回撤计算、成交量放量检测、技术指标查询等接口

## 安装与配置

### 1. 确保已安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 Tushare Token

请确保已在项目根目录配置好 `.env` 文件，包含 `TUSHARE_TOKEN`。

## 使用方法

### 命令行方式

```bash
# 同步所有行情数据（股票 + 指数）
python scripts/market_quota_syncer/cli.py --sync-all

# 仅同步所有股票行情
python scripts/market_quota_syncer/cli.py --sync-stocks

# 同步指定股票行情（自动增量同步）
python scripts/market_quota_syncer/cli.py --sync-stock 000001.SZ

# 仅同步所有指数行情
python scripts/market_quota_syncer/cli.py --sync-indices

# 同步指定指数行情（自动增量同步）
python scripts/market_quota_syncer/cli.py --sync-index 000001.SH

# 限制同步股票数量（用于测试）
python scripts/market_quota_syncer/cli.py --sync-stocks --max-stocks 10

# 设置请求间隔时间
python scripts/market_quota_syncer/cli.py --sync-all --delay 0.5

# 查询历史行情
python scripts/market_quota_syncer/cli.py --query-prices 000001.SZ

# 查询技术指标
python scripts/market_quota_syncer/cli.py --query-indicators 000001.SZ

# 计算最大回撤
python scripts/market_quota_syncer/cli.py --query-drawdown 000001.SZ --drawdown-window 252

# 检测成交量放量
python scripts/market_quota_syncer/cli.py --query-volume 000001.SZ

# 查看同步状态
python scripts/market_quota_syncer/cli.py --status

# 指定数据库文件
python scripts/market_quota_syncer/cli.py --db my_quotes.db --sync-all
```

### Python 脚本方式

```python
from scripts.market_quota_syncer import MarketQuotaSyncer

# 初始化行情同步器
syncer = MarketQuotaSyncer("stock_data.db")

# 同步所有数据
syncer.sync_all()

# 同步单只股票（自动增量同步 + 计算技术指标）
syncer.sync_single_stock("000001.SZ")

# 同步所有指数
syncer.sync_all_indices()

# 获取历史行情
df = syncer.get_history_prices("000001.SZ")

# 获取技术指标
df_indicators = syncer.get_indicators("000001.SZ")

# 计算最大回撤
max_drawdown, df_drawdown = syncer.calculate_drawdown("000001.SZ", window=252)

# 检测成交量放量
is_surge, ratio = syncer.detect_volume_surge("000001.SZ")
```

### 运行示例

```bash
# 先同步一些测试数据
python scripts/market_quota_syncer/cli.py --sync-indices

# 然后运行示例
python scripts/market_quota_syncer/example_usage.py
```

## 模块说明

- **database.py** - 数据库管理模块，包含 `MarketQuotaDB` 类，负责数据库表初始化和数据存取
- **fetcher.py** - 数据获取模块，包含 `MarketQuotaFetcher` 类，负责从 Tushare 获取行情数据和复权因子
- **indicators.py** - 技术指标计算模块，包含 `MarketTechnicalIndicators` 类，负责计算 MA、MACD、KDJ、RSI、BOLL 等技术指标
- **syncer.py** - 主同步器类，包含 `MarketQuotaSyncer` 类，整合数据库和数据获取功能
- **cli.py** - 命令行接口，提供命令行操作
- **example_usage.py** - 使用示例

## 数据库表结构

### fact_daily_quotes（个股日线行情表）
| 字段 | 类型 | 说明 |
|-----|------|------|
| ts_code | TEXT | 股票代码 |
| trade_date | TEXT | 交易日期 |
| open | REAL | 开盘价 |
| high | REAL | 最高价 |
| low | REAL | 最低价 |
| close | REAL | 收盘价 |
| pre_close | REAL | 昨收价 |
| change | REAL | 涨跌额 |
| pct_chg | REAL | 涨跌幅 |
| vol | REAL | 成交量（手） |
| amount | REAL | 成交额（千元） |
| adj_factor | REAL | 复权因子 |
| adj_open | REAL | 前复权开盘价 |
| adj_high | REAL | 前复权最高价 |
| adj_low | REAL | 前复权最低价 |
| adj_close | REAL | 前复权收盘价 |

### fact_index_daily（指数日线行情表）
| 字段 | 类型 | 说明 |
|-----|------|------|
| ts_code | TEXT | 指数代码 |
| trade_date | TEXT | 交易日期 |
| open | REAL | 开盘价 |
| high | REAL | 最高价 |
| low | REAL | 最低价 |
| close | REAL | 收盘价 |
| pre_close | REAL | 昨收价 |
| change | REAL | 涨跌额 |
| pct_chg | REAL | 涨跌幅 |
| vol | REAL | 成交量（手） |
| amount | REAL | 成交额（千元） |

### market_indicators（技术指标表）
| 字段 | 类型 | 说明 |
|-----|------|------|
| ts_code | TEXT | 股票代码 |
| trade_date | TEXT | 交易日期 |
| ma5 | REAL | 5日均线 |
| ma10 | REAL | 10日均线 |
| ma20 | REAL | 20日均线 |
| ma30 | REAL | 30日均线 |
| ma60 | REAL | 60日均线 |
| ma120 | REAL | 120日均线 |
| macd | REAL | MACD 线 |
| macd_signal | REAL | MACD 信号线 |
| macd_hist | REAL | MACD 柱状图 |
| kdj_k | REAL | KDJ K 值 |
| kdj_d | REAL | KDJ D 值 |
| kdj_j | REAL | KDJ J 值 |
| rsi6 | REAL | RSI 6日 |
| rsi12 | REAL | RSI 12日 |
| rsi24 | REAL | RSI 24日 |
| boll_upper | REAL | 布林带上轨 |
| boll_mid | REAL | 布林带中轨 |
| boll_lower | REAL | 布林带下轨 |

## Agent 决策接口

### get_history_prices(ts_code, start_date, end_date, is_index=False)
获取一段连续的复权行情数据。

### get_indicators(ts_code, start_date, end_date)
获取技术指标数据。

### calculate_drawdown(ts_code, window=252, is_index=False)
计算过去 X 天的最大回撤。

### detect_volume_surge(ts_code, short_window=5, long_window=20)
识别最近 5 日成交量是否显著超过过去 20 日均值（底部放量逻辑）。

## 内置指数列表

- `000001.SH` - 上证指数
- `399001.SZ` - 深证成指
- `000300.SH` - 沪深300
- `399006.SZ` - 创业板指
- `000852.SH` - 中证1000

## 更新策略建议 ⏰

| 数据类型 | 更新频率 | 说明 |
|---------|---------|------|
| 个股行情 | 每日 18:00 后 | 增量同步，从最后更新日期开始下载 |
| 指数行情 | 每日 18:00 后 | 增量同步，从最后更新日期开始下载 |
| 技术指标 | 同步行情时自动计算 | 每次同步行情时自动重新计算技术指标 |

### 推荐更新时间
- 个股行情：每日 18:00 - 20:00（收盘后数据完整）
- 指数行情：每日 18:00 - 20:00

## 注意事项

1. **Tushare 积分**：日线行情接口需要至少 120 积分，请确保账户有足够积分
2. **请求频率**：已内置 0.3 秒的 API 调用间隔，避免触发限流
3. **数据量**：全量同步 5000+ 股票可能需要较长时间，建议先测试同步指数
4. **复权计算**：采用前复权方式，以最新价格为基准回溯历史价格
5. **数据安全**：数据库文件建议定期备份

## 前复权计算说明

前复权价格计算公式：

```
前复权价格 = 原始价格 × 当日复权因子 / 最新复权因子
```

这样可以保证：
- 最新价格与交易软件一致
- 历史价格考虑了分红送股的影响
- 便于 Agent 进行波动率分析和长线决策