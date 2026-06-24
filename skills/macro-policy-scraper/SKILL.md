---
name: macro-policy-scraper
description: 中国宏观政策抓取与分析工具，支持获取政策聚焦、行业影响分析、安全期判断、关键词/日期范围查询、数据更新等功能。当用户提到政策分析、行业影响、宏观环境判断、政策查询、行业利好利空分析时自动触发。
---

# 宏观政策分析技能

## 核心功能
1. 抓取中国政府政策、行业新闻、监管动态信息
2. 分析政策对各行业/概念的利好/利空影响
3. 判断当前宏观投资安全期
4. 按关键词/日期范围查询历史政策
5. 输出结构化的政策分析报告

## 动态工作流程（基于前置结果自动执行）
所有步骤自动基于上一步的输出结果动态调用工具，无需用户手动指定参数：

### 步骤1：基础数据获取
根据用户请求的时间范围，自动执行以下命令：
```bash
cd /workspace/stock_downloader && python ./scripts/macro_policy_scrapper/cli.py --policy-focus {{days}}
cd /workspace/stock_downloader && python ./scripts/macro_policy_scrapper/cli.py --safe-period 14
# 官方权威渠道搜索（必看，决定基本面）
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:cninfo.com.cn {{keyword}} 公告 财报 政策" --max-results 3
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:sse.com.cn 政策 监管动态" --max-results 2
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:szse.cn 政策 监管动态" --max-results 2
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:csrc.gov.cn 最新政策" --max-results 2
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:pbc.gov.cn 货币政策 金融数据" --max-results 2
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:stats.gov.cn 宏观经济数据" --max-results 2
```
默认时间范围为过去30天，若用户指定其他时间范围则使用用户指定值。搜索关键词自动从用户请求中提取，若无明确关键词则使用"最新宏观政策 行业影响"作为默认搜索词。

### 步骤2：行业影响自动分析
基于步骤1返回的`policy_focus`中的行业列表，自动对每个行业执行影响分析：
```bash
cd /workspace/stock_downloader && python ./scripts/macro_policy_scrapper/cli.py --check-impact "{{sector_name}}"
```
自动遍历所有识别出的行业，无需手动输入行业名称。

### 步骤3：媒体新闻补充搜索
基于步骤1和步骤2识别出的关键词和行业，自动调用Tavily搜索相关新闻，覆盖全渠道信息：
```bash
# 极速快讯（短线/盘中必备）
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:cls.cn {{keyword}} 快讯 最新消息" --max-results 3
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:wallstreetcn.com {{keyword}} 全球联动 快评" --max-results 2
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:10jqka.com.cn {{keyword}} 异动 龙虎榜" --max-results 2
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:eastmoney.com {{keyword}} 快讯 行情联动" --max-results 2

# 综合财经门户（深度+数据）
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:eastmoney.com {{keyword}} 研报 财报 行业分析" --max-results 3
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:finance.sina.com.cn {{keyword}} 政策解读 全球市场" --max-results 3
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:caixin.com {{keyword}} 深度调查 政策解读" --max-results 2
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:yicai.com {{keyword}} 行业趋势 政策分析" --max-results 2
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:nbd.com.cn {{keyword}} 行业新闻 公司动态" --max-results 2

# 投资社区（情绪+逻辑+挖掘）
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:xueqiu.com {{keyword}} 个股逻辑 调研纪要" --max-results 3
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:taoguba.com.cn {{keyword}} 热点题材 涨停复盘" --max-results 2
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:jiuyangongshe.com {{keyword}} 游资视角 题材挖掘" --max-results 2

# 海外/机构（全球化与专业数据）
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:cn.reuters.com {{keyword}} 国际资本 大宗商品" --max-results 2
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:bloomberg.com {{keyword}} 全球政策 汇率" --max-results 2
${PYTHON_BIN:-python3} ${TAVILY_SEARCH_SCRIPT:-/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py} --query "site:hibor.com.cn {{keyword}} 机构研报 产业链数据" --max-results 2
```
自动使用步骤1和步骤2识别出的关键词进行搜索，覆盖所有权威财经渠道，确保信息全面性和时效性。

### 步骤4：结果聚合与输出
自动整合所有步骤的结果，输出结构化JSON报告：
```json
{
  "period": "{{start_date}} to {{end_date}}",
  "macro_safe": true/false,
  "policy_focus": [
    {"sector": "行业名称", "keywords": ["关键词1", "关键词2"], "importance": 1-5, "sentiment": "积极/中性/消极"},
  ],
  "sector_analysis": [
    {"sector": "行业名称", "impact": "利好/利空/中性", "policy_count": 数量, "reason": "影响原因"},
  ],
  "media_news": [
    {"source": "来源", "title": "新闻标题", "url": "链接", "related_sectors": ["关联行业"]},
  ],
  "summary": "整体分析结论"
}
```

## 专用命令（用户可直接调用）
1. `分析最近{{N}}天政策` - 返回指定天数的政策聚焦和行业影响
2. `判断当前宏观安全期` - 返回最近14天的宏观环境安全情况
3. `分析{{行业}}政策影响` - 单独分析指定行业的政策影响
4. `查询政策关键词{{关键词}}` - 按关键词查询相关政策
5. `更新政策数据` - 更新最新的政策数据库

## 注意事项
1. 优先使用本地工具获取结构化数据，再用网络搜索补充最新内容
2. 自动去重重复的政策和新闻信息
3. 政策重要程度按1-5星评分，5星为最高级
4. 所有时间默认使用北京时间
5. 输出结果保留原始政策来源链接方便溯源
