# 宏观政策抓取工具 (Macro Policy Scrapper)

这是Agent系统的"宏观政策感知器"，用于捕获各类新闻、政策文件等文本，并提取关键信息。

## 功能概述

| 功能 | 描述 | 实现方式 | Agent调用 |
|------|------|----------|-----------|
| 新闻快讯抓取 | 每日实时财经新闻 | Tushare news | `fetch_news` |
| 新闻联播文本 | 每晚《新闻联播》文字实录 | 爬虫/第三方API | `fetch_xwlb` |
| 重要会议纪要 | 国常会、政治局会议等 | 政府网站爬虫 | `fetch_meeting` |
| 经济日历 | 宏观数据发布时间点 | Tushare eco_cal | `fetch_eco_cal` |

## 数据存储

- **表名**: `fact_macro_narratives`
- **内容**: 非结构化/半结构化的文本，含时间戳、来源、关键词标签、重要程度评分
- **更新策略**: 新闻类实时下载，历史数据不再重复抓取
- **Agent专属接口**:
  - `get_current_policy_focus(days=30)` - 获取当前政策聚焦点（用于舆情监控）
  - `check_event_impact(sector, days=30)` - 检查特定行业的事件影响
  - `is_macro_safe_period(days=14)` - 判断当前是否为宏观安全期（无强监管、加息等）

## 项目结构

```
scripts/macro_policy_scrapper/
├── __init__.py       # 模块初始化文件
├── database.py       # 数据库管理模块
├── fetcher.py        # 数据获取模块
├── scrapper.py       # 主抓取器类
├── cli.py            # 命令行接口
├── example_usage.py  # 使用示例
├── README.md         # 使用说明文档
└── requirement.txt   # 需求文档
```

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
python scripts/macro_policy_scrapper/cli.py --update-all

# 单独更新新闻快讯
python scripts/macro_policy_scrapper/cli.py --update-news

# 单独更新经济日历
python scripts/macro_policy_scrapper/cli.py --update-eco-cal

# 指定日期范围更新
python scripts/macro_policy_scrapper/cli.py --update-news --start-date 20240301 --end-date 20240331

# 强制更新（不检查是否已存在）
python scripts/macro_policy_scrapper/cli.py --update-all --force

# 按关键词查询
python scripts/macro_policy_scrapper/cli.py --query-keyword "人工智能"

# 按日期范围查询
python scripts/macro_policy_scrapper/cli.py --query-date-range 20240301 20240331

# 获取当前政策聚焦（天数）
python scripts/macro_policy_scrapper/cli.py --policy-focus 30

# 检查特定行业事件影响
python scripts/macro_policy_scrapper/cli.py --check-impact "人工智能"

# 判断宏观安全期（天数）
python scripts/macro_policy_scrapper/cli.py --safe-period 14

# 查询最后更新时间
python scripts/macro_policy_scrapper/cli.py --last-update news

# 指定数据库文件
python scripts/macro_policy_scrapper/cli.py --db my_stocks.db --update-all
```

### Python脚本方式

```python
from scripts.macro_policy_scrapper import MacroPolicyScrapper

# 初始化宏观政策抓取器
scrapper = MacroPolicyScrapper("stock_data.db")

# 更新所有数据
scrapper.update_all()

# 获取当前政策聚焦（Agent接口）
focus = scrapper.get_current_policy_focus(days=30)
print(focus['message'])

# 检查特定行业的事件影响（Agent接口）
impact = scrapper.check_event_impact("人工智能", days=30)
print(impact['message'])

# 判断当前是否为宏观安全期（Agent接口）
safe = scrapper.is_macro_safe_period(days=14)
print(safe['message'])

# 按日期范围查询
df = scrapper.get_narratives_by_date_range("20240301", "20240331")

# 按关键词查询
df = scrapper.get_narratives_by_keyword("人工智能")

# 获取最后更新时间
last_update = scrapper.get_last_update_time("news")
```

### 运行示例

```bash
# 先更新数据
python scripts/macro_policy_scrapper/cli.py --update-all

# 然后运行示例
python scripts/macro_policy_scrapper/example_usage.py
```

## 模块说明

- **database.py** - 数据库管理模块，包含 `MacroPolicyScrapperDatabase` 类，负责数据库表初始化和数据存取
- **fetcher.py** - 数据获取模块，包含 `DataFetcher` 类，负责从Tushare和其他来源获取数据
- **scrapper.py** - 主抓取器类，包含 `MacroPolicyScrapper` 类，整合数据库和数据获取功能
- **cli.py** - 命令行接口，提供命令行操作
- **example_usage.py** - 使用示例

## 数据处理特性

### 1. 噪音过滤
- 自动过滤噪音新闻（涨停、跌停、机构预测、个股分析等）
- 保留真正的政策和宏观新闻

### 2. 关键词提取
- 预设行业关键词库（人工智能、半导体、新能源、数字经济等）
- 自动识别新闻涉及的行业和主题

### 3. 情感分析
- 支持四种情感类型：支持、稳健、规范、严打
- 基于关键词进行情感极性判断

### 4. 重要程度评分
- 1-5分的重要程度评分
- 基于来源权威性、关键词重要性等因素综合评分

### 5. 内存优化
- 逐条保存数据，避免内存占用过大
- 先查询后下载，避免重复API调用

## 更新策略建议 ⏰

| 数据类型 | 更新频率 | 说明 |
|---------|---------|------|
| 新闻快讯 | 每日多次 | 用于舆情监控，建议每小时或每2小时检查一次 |
| 经济日历 | 每周一次 | 不需要太频繁，建议每周日更新 |
| 新闻联播 | 每日一次 | 固定时间抓取，建议每晚20:30后 |
| 重要会议纪要 | 按需 | 按需检查 |

### 推荐更新时间
- 新闻快讯：每日 9:00, 11:00, 14:00, 16:00, 20:00
- 经济日历：每周日 20:00
- 新闻联播：每日 20:30 - 21:00

## Agent 接口说明

### `get_current_policy_focus(days=30, top_n=5)`
获取当前政策聚焦点，用于舆情监控。
- **输入**: 统计天数、返回前N个
- **输出**: 包含政策聚焦信息的字典，包括message、focus_sectors、top_keywords等

### `check_event_impact(sector, days=30)`
检查特定行业的事件影响。
- **输入**: 行业名称、检查天数
- **输出**: 包含事件影响信息的字典，包括message、total_events、important_events、events等

### `is_macro_safe_period(days=14)`
判断当前是否为宏观安全期（无强监管、加息等）。
- **输入**: 检查天数
- **输出**: 包含安全期判断信息的字典，包括is_safe、message、risk_signals、support_signals等

## 注意事项

1. **Tushare积分**：部分接口需要积分，请确保账户有足够积分
2. **请求频率**：已内置合理的更新逻辑，避免频繁调用
3. **数据去重**：系统会自动检查并避免重复保存相同数据
4. **数据安全**：数据库文件建议定期备份
5. **内存优化**：逐条保存数据，避免内存占用过大
6. **API节省**：历史数据不再重复抓取，减少API使用