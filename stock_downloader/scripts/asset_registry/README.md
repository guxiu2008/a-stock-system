# 资产注册表 (Asset Registry)

这是Agent系统的"地图"，管理股票的基础信息、行业分类、概念分类和交易日历。

## 项目结构

```
scripts/asset_registry/
├── __init__.py       # 模块初始化文件
├── database.py       # 数据库管理模块
├── fetcher.py        # 数据获取模块
├── registry.py       # 主注册表类
├── cli.py            # 命令行接口
├── example_usage.py  # 使用示例
└── README.md         # 使用说明文档
```

## 功能特性

1. **股票基础信息管理**：存储股票代码、名称、所属地域、行业、上市日期等
2. **行业分类管理**：申万行业分类，支持按行业查询股票
3. **概念分类管理**：概念板块分类（预留）
4. **交易日历管理**：存储交易日历，支持查询是否为交易日
5. **增量更新**：支持数据的定期更新和状态记录

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
# 更新所有数据
python scripts/asset_registry/cli.py --update-all

# 单独更新股票基础信息
python scripts/asset_registry/cli.py --update-stock

# 单独更新行业分类
python scripts/asset_registry/cli.py --update-industry

# 单独更新交易日历
python scripts/asset_registry/cli.py --update-calendar

# 查询指定股票信息
python scripts/asset_registry/cli.py --query-stock 000001.SZ

# 查询指定行业的股票
python scripts/asset_registry/cli.py --query-industry 银行

# 指定数据库文件
python scripts/asset_registry/cli.py --db my_stocks.db --update-all
```

### Python脚本方式

```python
from scripts.asset_registry import AssetRegistry

# 初始化资产注册表
registry = AssetRegistry("stock_data.db")

# 更新所有数据
registry.update_all()

# 查询股票信息
df = registry.get_stock_info(ts_code="000001.SZ")

# 按行业查询股票
industry_stocks = registry.get_stocks_by_industry("银行")

# 判断是否为交易日
is_trading = registry.is_trading_day("20240327")

# 获取最后更新时间
last_update = registry.get_last_update_time("stock_basic")
```

### 运行示例

```bash
# 先更新数据
python scripts/asset_registry/cli.py --update-all

# 然后运行示例
python scripts/asset_registry/example_usage.py
```

## 模块说明

- **database.py** - 数据库管理模块，包含 `AssetRegistryDB` 类，负责数据库表初始化和数据存取
- **fetcher.py** - 数据获取模块，包含 `DataFetcher` 类，负责从Tushare获取数据
- **registry.py** - 主注册表类，包含 `AssetRegistry` 类，整合数据库和数据获取功能
- **cli.py** - 命令行接口，提供命令行操作
- **example_usage.py** - 使用示例

## 更新策略建议 ⏰

| 数据类型 | 更新频率 | 说明 |
|---------|---------|------|
| 股票基础档案 | 每日收盘后 | 每日更新，保持股票列表最新 |
| 行业分类 | 每周一次 | 每周更新行业分类映射关系 |
| 交易日历 | 每年年初 | 每年1月更新下一年的交易日历 |

### 推荐更新时间
- 股票基础档案：每日 17:00 后
- 行业分类：每周日 20:00
- 交易日历：每年 1月1日

## 注意事项

1. **Tushare积分**：部分接口需要积分，请确保账户有足够积分
2. **请求频率**：已内置合理的更新逻辑，避免频繁调用
3. **数据量**：首次更新可能需要较长时间
4. **数据安全**：数据库文件建议定期备份