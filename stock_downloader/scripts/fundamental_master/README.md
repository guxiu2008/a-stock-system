# 财务护城河数据工具 (Fundamental Master)

这是Agent系统的"财务深度分析器"，获取全量A股历史至今的所有定期报告及衍生财务指标，支持 Agent 执行"基本面三问"逻辑。

## 项目结构

```
scripts/fundamental_master/
├── __init__.py       # 模块初始化文件
├── database.py       # 数据库管理模块
├── fetcher.py        # 数据获取模块
├── master.py         # 主工具类（包含 Agent 专属接口）
├── cli.py            # 命令行接口
├── example_usage.py  # 使用示例
├── requirement.txt   # 需求文档
└── README.md         # 使用说明文档
```

## 功能特性

1. **多表数据整合**：自动获取并合并资产负债表、利润表、现金流量表、财务指标表
2. **报告期管理**：支持按季度报告期（0331, 0630, 0930, 1231）下载数据
3. **数据清洗**：处理空值，兼容不同行业的财报字段差异
4. **Agent 专属接口**：提供高层 API 供 OpenClaw Agent 调用
5. **深度回溯**：支持历史数据回溯10年，跨越完整经济周期

## Agent 决策逻辑（基本面三问）

脚本下载的数据直接服务于以下 Agent 逻辑：
- **ROE 是否稳定？** —— 考察公司赚钱的效率和持续性
- **现金流是否覆盖利润？** —— 识别"纸面富贵"，过滤掉回款困难的垃圾公司
- **负债率是否健康？** —— 评估财务杠杆风险，确保公司能活过行业寒冬

## 安装与配置

### 1. 确保已安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置Tushare Token

请确保已在项目根目录配置好 `.env` 文件，包含 `TUSHARE_TOKEN`。

### 3. 先运行 Asset Registry

在使用 Fundamental Master 前，请先运行 Asset Registry 来下载股票基本信息：

```bash
# 更新股票列表
python -m scripts.asset_registry.cli --update-basic
```

这一步很重要，因为 Fundamental Master 会直接从数据库读取股票列表，而不是重复调用 API。

## 使用方法

### 命令行方式

```bash
# 更新指定股票的数据（推荐，速度快）
python -m scripts.fundamental_master.cli --update --ts-code 600519.SH --period 20231231

# 更新所有股票的数据（注意：这可能需要较长时间）
python -m scripts.fundamental_master.cli --update --period 20231231

# 更新过去10年的数据（注意：这可能需要较长时间）
python -m scripts.fundamental_master.cli --update-10y

# 查询财务报告
python -m scripts.fundamental_master.cli --query 600519.SH

# 获取财务健康评分（Agent 接口）
python -m scripts.fundamental_master.cli --health-score 600519.SH

# 筛选护城河股票（Agent 接口）
python -m scripts.fundamental_master.cli --find-moat --min-roe 15

# 检测财务预警信号（Agent 接口）
python -m scripts.fundamental_master.cli --detect-flags 600519.SH

# 指定数据库文件
python -m scripts.fundamental_master.cli --db my_stocks.db --update --period 20231231
```

### Python脚本方式

```python
from scripts.fundamental_master import FundamentalMaster

# 初始化
master = FundamentalMaster("stock_data.db")

# 更新数据
master.update_financial_data(period="20231231")

# 更新过去10年的数据
master.update_last_10_years()

# 查询财务报告
df = master.get_financial_reports(ts_code="600519.SH")

# ==================== Agent 专属 Tool 接口 ====================

# 1. 获取财务健康评分
health_score = master.get_financial_health_score("600519.SH")
print(health_score)

# 2. 筛选具有护城河的股票
moat_stocks = master.find_moat_stocks(min_roe=15)
print(moat_stocks)

# 3. 检测财务预警信号
red_flags = master.detect_accounting_red_flags("600519.SH")
print(red_flags)
```

### 运行示例

```bash
# 先更新数据
python -m scripts.fundamental_master.cli --update --period 20231231

# 然后运行示例
python scripts/fundamental_master/example_usage.py
```

## Agent 专属 Tool 接口详情

### 1. get_financial_health_score(ts_code)
**逻辑**：获取过去 5 年的 ROE 均值、现金流覆盖率和最新负债率
**返回**：健康报告字典

```python
{
  "ts_code": "600519.SH",
  "status": "success",
  "latest_end_date": "20231231",
  "roe_mean_5y": 24.5,
  "cashflow_coverage_mean_5y": 1.2,
  "latest_debt_to_assets": 20.3,
  "summary": "ROE 表现优秀，过去 5 年均值 24.50%; 现金流覆盖良好，均值 1.20; 负债率健康，当前 20.30%"
}
```

### 2. find_moat_stocks(industry, min_roe=15)
**逻辑**：筛选出 ROE 持续稳定在 min_roe 以上的股票
**返回**：符合条件的股票列表

### 3. detect_accounting_red_flags(ts_code)
**逻辑**：如果"应收账款"增速远超"营业收入"增速，触发预警
**返回**：预警信号字典

## 数据库表结构

### fact_financial_reports
存储财务报告数据，主要字段：
- `ts_code` - 股票代码
- `end_date` - 报告期 (如 20251231)
- `ann_date` - 实际公告日期
- `roe` - 净资产收益率
- `net_profit` - 净利润
- `ncf_from_oa` - 经营性现金流净额
- `debt_to_assets` - 资产负债率

## 模块说明

- **database.py** - 数据库管理模块，包含 `FundamentalMasterDB` 类
- **fetcher.py** - 数据获取模块，包含 `FinancialDataFetcher` 类
- **master.py** - 主工具类，包含 `FundamentalMaster` 类，整合所有功能
- **cli.py** - 命令行接口
- **example_usage.py** - 使用示例

## 更新策略建议 ⏰

| 数据类型 | 更新频率 | 说明 |
|---------|---------|------|
| 财务报告 | 财报季（4月、8月） | 每年4月和8月是发报高峰期，重点更新 |
| 深度回溯 | 首次使用时 | 建议历史数据至少回溯10年 |

### 推荐更新时间
- 深度回溯（10年）：首次使用时运行一次
- 季度更新：
  - 4月（年报+一季报）：4月1日 - 4月30日
  - 8月（中报）：8月1日 - 8月31日
  - 10月（三季报）：10月1日 - 10月31日

### 更新建议
- **财报季效应**：每年的4月和8月是发报高峰期，增量同步脚本应在这些月份提高运行频次
- **财报季运行**：4月和8月建议每周运行2-3次更新
- **非财报季**：可每月运行一次检查是否有补充公告

## 注意事项（避坑指南）

1. **积分限流**：`fina_indicator` 是高频接口，大批量下载时已内置 `time.sleep`
2. **财报季节效应**：每年的4月和8月是发报高峰期，增量同步脚本应在这些月份提高运行频次
3. **利润表 vs 现金流**：长线思维的核心是"现金为王"，已确保 cashflow 数据的准确性
4. **空值处理**：金融类公司（银行/保险）的报表字段与工业企业不同，脚本已具备兼容性
5. **增量保存**：获取多只股票数据时，每只股票获取后立即保存，即使中途中断也不会丢失已获取的数据
6. **数据量**：首次更新过去10年数据可能需要较长时间，请耐心等待
