# Stock Downloader - 股票数据下载系统

这是一个完整的A股数据下载和分析系统，包含多个独立模块，为Agent系统提供数据底座。

## 模块概览

| 模块 | 名称 | 更新频率 | 主要功能 |
|------|------|----------|----------|
| asset_registry | 资产注册表 | 股票基础档案每日收盘后；行业分类每周一次；交易日历每年年初 | 股票基础信息、行业分类、概念分类、交易日历 |
| market_quota_syncer | 行情同步器 | 每日 18:00 后 | 个股行情、指数行情、复权因子、技术指标 |
| money_flow_analyst | 资金流向分析 | 每日收盘后 | 北向资金、融资融券、趋势分析 |
| dividend_yield_tracker | 股息率追踪器 | 历史数据首次初始化后，日常每日收盘后检查最新分红 | 分红历史、股息率计算、高股息筛选 |
| fundamental_master | 财务护城河工具 | 财报季（4月、8月）；首次使用时深度回溯10年 | 财务报告、ROE分析、现金流分析 |
| macro_policy_scrapper | 宏观政策抓取器 | 新闻快讯每日多次；经济日历每周一次；新闻联播每日一次 | 新闻快讯、经济日历、政策抓取、舆情分析 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 Tushare Token

复制 `.env.example` 为 `.env`，并填写你的 Tushare Token：

```bash
cp .env.example .env
# 编辑 .env 文件，填写 TUSHARE_TOKEN
```

### 3. 初始化基础数据

首先运行资产注册表来建立股票基础信息：

```bash
python scripts/asset_registry/cli.py --update-all
```

## 推荐更新顺序

### 首次初始化

1. asset_registry - 建立股票基础信息
2. market_quota_syncer - 下载行情数据
3. fundamental_master - 下载财务数据（深度回溯10年）
4. dividend_yield_tracker - 下载分红历史（10年）
5. money_flow_analyst - 下载资金流向数据
6. macro_policy_scrapper - 下载宏观政策数据

### 日常更新（每日）

1. market_quota_syncer - 每日 18:00 后同步行情
2. money_flow_analyst - 收盘后同步资金流向
3. macro_policy_scrapper - 新闻快讯每日多次
4. dividend_yield_tracker - 检查最新分红公告

### 定期更新

- asset_registry - 每周更新行业分类
- fundamental_master - 财报季（4月、8月）更新财务报告
- dividend_yield_tracker - 分红季检查新分红

## 项目结构

```
stock_downloader/
├── scripts/
│   ├── asset_registry/          # 资产注册表
│   ├── market_quota_syncer/     # 行情同步器
│   ├── money_flow_analyst/      # 资金流向分析
│   ├── dividend_yield_tracker/  # 股息率追踪器
│   ├── fundamental_master/       # 财务护城河工具
│   ├── macro_policy_scrapper/    # 宏观政策抓取器
│   └── lib/                      # 共享库和数据库表定义
├── config.py                     # 配置文件
├── requirements.txt              # 依赖
├── .env                          # 环境变量
└── stock_data.db                 # SQLite 数据库（运行后生成）
```

## 数据库表

所有模块共享同一个 SQLite 数据库文件 `stock_data.db`，主要表结构：

### 基础信息表
- `dim_stock_info` - 股票基础信息
- `dim_trade_calendar` - 交易日历
- `map_industry_stock` - 行业分类映射
- `map_concept_stock` - 概念分类映射

### 行情数据表
- `fact_daily_quotes` - 个股日线行情
- `fact_index_daily` - 指数日线行情
- `market_indicators` - 技术指标

### 财务数据表
- `fact_financial_reports` - 财务报告
- `fact_dividend_history` - 分红历史

### 资金流向表
- `fact_money_flow` - 资金流向数据

### 宏观政策表
- `fact_macro_narratives` - 宏观叙事

### 日志表
- 各模块的更新日志表

## 注意事项

1. **Tushare 积分**：部分接口需要一定积分，请确保账户有足够积分
2. **请求频率**：所有模块都内置了请求间隔，避免触发限流
3. **数据量**：首次全量下载可能需要较长时间
4. **数据库备份**：建议定期备份 `stock_data.db`

## 各模块详细文档

请查看各子目录的 README.md 获取详细使用说明：

- [资产注册表](./scripts/asset_registry/README.md)
- [行情同步器](./scripts/market_quota_syncer/README.md)
- [资金流向分析](./scripts/money_flow_analyst/README.md)
- [股息率追踪器](./scripts/dividend_yield_tracker/README.md)
- [财务护城河工具](./scripts/fundamental_master/README.md)
- [宏观政策抓取器](./scripts/macro_policy_scrapper/README.md)