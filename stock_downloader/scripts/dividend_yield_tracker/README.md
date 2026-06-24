# 股息率追踪器 (Dividend Yield Tracker)

追踪A股市场的分红历史数据，筛选高股息股票，分析分红可持续性，帮助发现"现金牛"股票。

## 项目结构

```
scripts/dividend_yield_tracker/
├── __init__.py       # 模块初始化文件
├── database.py       # 数据库管理模块
├── fetcher.py        # 数据获取模块
├── tracker.py        # 主追踪器类
├── cli.py            # 命令行接口
├── example_usage.py  # 使用示例
└── README.md         # 使用说明文档
```

## 功能特性

1. **分红历史数据管理**：存储股票的分红记录、分红年度、每股派息等
2. **静态股息率计算**：基于最新分红和当前股价计算股息率
3. **派息率计算**：关联财务数据计算分红占净利润的比例
4. **高股息股票筛选**：自动筛选股息率高于阈值的股票（现金牛）
5. **分红可持续性分析**：基于连续分红年数、分红增长率评估可持续性
6. **即将分红提醒**：跟踪已公告但未到登记日的股票
7. **智能数据更新**：避免重复下载历史数据，按年度分批保存

## 安装与配置

### 1. 确保已安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置Tushare Token

请确保已在项目根目录配置好 `.env` 文件，包含 `TUSHARE_TOKEN`。

## 使用方法

### 命令行方式

```bash
# 【首次使用】同步历史分红数据（默认10年）
# 用于初始化数据库，下载过去多年的历史分红记录
python scripts/dividend_yield_tracker/cli.py --sync-history

# 同步指定年数的历史数据（如5年）
python scripts/dividend_yield_tracker/cli.py --sync-history 5

# 强制更新历史数据（即使数据库中已存在）
python scripts/dividend_yield_tracker/cli.py --sync-history 10 --force

# 【日常更新】同步最新分红数据
# 只获取当前年度的分红公告，用于日常监控
python scripts/dividend_yield_tracker/cli.py --sync-latest

# 获取高股息股票列表（默认最低5%）
python scripts/dividend_yield_tracker/cli.py --cash-cow

# 获取股息率大于3%的股票
python scripts/dividend_yield_tracker/cli.py --cash-cow 0.03

# 检查指定股票的分红可持续性
python scripts/dividend_yield_tracker/cli.py --check-sustainability 000001.SZ

# 获取即将分红的股票列表
python scripts/dividend_yield_tracker/cli.py --upcoming

# 计算指定股票的静态股息率
python scripts/dividend_yield_tracker/cli.py --yield 000001.SZ

# 指定数据库文件
python scripts/dividend_yield_tracker/cli.py --db my_stocks.db --sync-history
```

### Python脚本方式

```python
from scripts.dividend_yield_tracker import DividendYieldTracker

# 初始化股息率追踪器
tracker = DividendYieldTracker("stock_data.db")

# 同步历史分红数据（10年）
count = tracker.sync_dividend_history(years=10)

# 同步最新分红数据
count = tracker.sync_latest_dividends()

# 计算静态股息率
dy = tracker.calculate_static_yield("000001.SZ")

# 检查分红可持续性
sustainability = tracker.check_dividend_sustainability("000001.SZ")

# 获取高股息股票列表（股息率 >= 5%）
cash_cows = tracker.get_cash_cow_list(min_yield=0.05)

# 获取即将分红的股票
upcoming = tracker.get_upcoming_dividends()
```

### 运行示例

```bash
# 先同步数据
python scripts/dividend_yield_tracker/cli.py --sync-history 10

# 然后运行示例
python scripts/dividend_yield_tracker/example_usage.py
```

## 模块说明

- **database.py** - 数据库管理模块，包含 `DividendYieldTrackerDatabase` 类，负责数据库表初始化和数据存取
- **fetcher.py** - 数据获取模块，包含 `DividendDataFetcher` 类，负责从Tushare获取分红数据
- **tracker.py** - 主追踪器类，包含 `DividendYieldTracker` 类，整合数据库和数据获取功能，提供核心业务逻辑
- **cli.py** - 命令行接口，提供命令行操作
- **example_usage.py** - 使用示例

## 数据优化策略

1. **按年度分批下载**：分红数据按年度逐一下载并保存，避免内存溢出
2. **重复数据检查**：下载前先检查数据库中是否已有该年度数据，避免重复API调用
3. **关联已有数据**：计算股息率时复用行情模块的股价数据和基本面模块的财务数据

## 更新策略建议 ⏰

| 数据类型 | 更新频率 | 说明 |
|---------|---------|------|
| 历史分红数据 | 首次初始化（仅一次） | 下载过去5-10年历史分红数据 |
| 最新分红公告 | 每日收盘后 | 只检查当前年度是否有新的分红公告 |
| 股息率计算 | 查询时实时 | 依赖最新股价，每次查询时实时计算 |

### 推荐更新时间
- 历史分红初始化：首次使用时运行一次（5-10年数据）
- 最新分红检查：每日 17:00 - 18:00
- 分红季（4-6月）：可以增加检查频率

### 命令使用场景
| 命令 | 使用场景 | 说明 |
|------|---------|------|
| `--sync-history` | 首次初始化 | 下载过去5-10年历史分红数据，按年度逐个处理 |
| `--sync-latest` | 日常监控 | 只获取当前年度的数据，快速检查新分红 |

**`--sync-history` vs `--sync-latest` 区别：**
- `--sync-history`：批量下载历史数据，按年度逐个处理，避免重复下载已存在的年度数据
- `--sync-latest`：只获取当前年度的数据，用于快速更新最近的分红公告

## 注意事项

1. **数据依赖**：计算股息率需要 `market_quota_syncer` 模块的股价数据
2. **派息率计算**：需要 `fundamental_master` 模块的财务数据
3. **Tushare积分**：`dividend` 接口需要2000积分
4. **请求频率**：已内置1秒间隔，避免频繁调用
5. **数据量**：首次更新可能需要较长时间（按年度分批处理）