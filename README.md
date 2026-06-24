# A-Stock System

A 股自动化选股、财报分析、新闻验证、单股评估、宏观政策分析和回测系统。目标是把所有 opencode skill、sub-agent、脚本和文档放在一个 GitHub 仓库里维护。

## 当前能力

- 每日选股：默认中期波段，先量化初筛 30 只，再财报硬筛、Tavily 联网新闻/公告验证、综合重排，最终输出 5 只。
- 短线选股：`--mode short`，适合 2~4 周波段。
- 单股评估：6 维度评分，给出买/观望/回避建议。
- 财报分析：营收、净利、ROE、毛利率、净利率、负债率、现金流、应收、分红。
- 新闻真实性识别：多来源交叉、官方公告权重、合作方/订单线索、财报合理性校验。
- Sub-agent：单股深度评估、大盘环境、宏观政策分析。
- 回测：保存 v2 策略历史验证代码和结果。

## 仓库结构

```text
a-stock-system/
├── skills/
│   ├── a-stock-advisor/          # 主 skill：选股、财报、新闻验证、单股评估
│   │   ├── SKILL.md
│   │   ├── README.md
│   │   ├── config.example.env
│   │   ├── scripts/
│   │   │   ├── daily_pick.py
│   │   │   ├── evaluate_stock.py
│   │   │   └── lib/
│   │   │       ├── cache.py
│   │   │       ├── db.py
│   │   │       ├── financials.py
│   │   │       ├── news_verifier.py
│   │   │       └── strategy.py
│   │   └── reference/
│   ├── tavily-search/            # vendored Tavily 搜索 skill，新闻验证依赖它
│   │   ├── SKILL.md
│   │   └── scripts/tavily_search.py
│   └── macro-policy-scraper/     # 宏观政策 skill
│       └── SKILL.md
├── agents/
│   └── stock-team/
│       ├── stock_deep_evaluator.md
│       ├── market_environment.md
│       └── macro_policy_analyst.md
├── stock_downloader/             # 数据底座代码，不提交 DB/venv/cache
├── backtest/                     # 策略回测代码
├── docs/
│   └── mindset.md
├── scripts/
│   └── install_opencode.sh       # 一键安装/软链 skills 和 agents
└── .gitignore
```

## 快速安装

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/a-stock-system.git
cd a-stock-system

# 2. （可选）复制并编辑环境变量
cp .env.example .env
# 编辑 .env，填写你的路径和 TAVILY_API_KEY

# 3. 一键安装到 opencode
./scripts/install_opencode.sh

# 4. 重启 opencode
```

安装脚本会自动完成：

- ✅ 软链所有 skills 到 `~/.config/opencode/skills/`
- ✅ 软链所有 sub-agents 到 `~/.config/opencode/agents/stock-team/`
- ✅ 创建每日报告存档目录（按 YYYY/MM 分月）
- ✅ 写入/更新 `~/.opencode/.env` 中的环境变量
- ✅ 脚本执行权限设置

## 环境变量配置

所有配置项见根目录 `.env.example`，支持两种方式配置：

### 方式一：项目根目录 `.env`（推荐，Git 管理）
```bash
cp .env.example .env
# 编辑 .env
```

### 方式二：全局 `~/.opencode/.env`
```bash
STOCK_DB_PATH=/workspace/stock_downloader/stock_data.db
PYTHON_BIN=/workspace/stock_downloader/venv/bin/python
TAVILY_API_KEY=你的 Tavily Key
TAVILY_SEARCH_SCRIPT=/workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py
A_STOCK_NEWS_CACHE=/tmp/a_stock_news_cache.json
A_STOCK_ARCHIVE_DIR=/workspace/a-stock-system/skills/a-stock-advisor/archive
```

如果没有 `TAVILY_API_KEY`，选股仍可运行，但新闻验证会降级为“未联网”。

## 使用方式

### opencode 对话

```text
今天按中期波段选股
今天按短线模式选股
深度分析 600519，给我买/卖/持建议
现在大盘环境怎么样？适合几成仓位？
分析最近30天政策对半导体的影响
```

### 命令行

```bash
# 默认：中期波段 + 财报筛选 + 联网新闻验证
/workspace/stock_downloader/venv/bin/python \
  /workspace/a-stock-system/skills/a-stock-advisor/scripts/daily_pick.py

# 快速模式：跳过联网新闻验证
/workspace/stock_downloader/venv/bin/python \
  /workspace/a-stock-system/skills/a-stock-advisor/scripts/daily_pick.py --fast

# 短线模式
/workspace/stock_downloader/venv/bin/python \
  /workspace/a-stock-system/skills/a-stock-advisor/scripts/daily_pick.py --mode short

# 自动存档报告（推荐每日运行）
/workspace/stock_downloader/venv/bin/python \
  /workspace/a-stock-system/skills/a-stock-advisor/scripts/daily_pick.py --archive

# 指定存档目录
/workspace/stock_downloader/venv/bin/python \
  /workspace/a-stock-system/skills/a-stock-advisor/scripts/daily_pick.py --archive --archive-dir /path/to/your/archive

# 单股评估
/workspace/stock_downloader/venv/bin/python \
  /workspace/a-stock-system/skills/a-stock-advisor/scripts/evaluate_stock.py 600519

# Tavily 搜索
/workspace/stock_downloader/venv/bin/python \
  /workspace/a-stock-system/skills/tavily-search/scripts/tavily_search.py \
  --query "贵州茅台 最新 公告 风险" --max-results 5
```

## 每日选股流程

1. 量化策略先生成 30 只候选。
2. 财报分析模块剔除硬风险和低质量财报。
3. Tavily 搜索公司新闻、公告、合作方、行业政策。
4. 新闻验证模块按来源可信度、多来源一致性、公告线索、合作方线索、财报匹配度打分。
5. 综合技术面、趋势、ROE、财报、新闻可信度重排。
6. 输出 5 只候选，标注可操作/观察池、买入区间、目标价、止损、风险收益比、淘汰样例。

## 报告存档与复盘

使用 `--archive` 参数会自动保存两种格式的报告到 `A_STOCK_ARCHIVE_DIR` 目录，按 `YYYY/MM` 分月存放：

```
archive/
├── 2026/
│   ├── 06/
│   │   ├── daily_pick_20260605_swing.json   # 完整结构化数据，编程复盘用
│   │   └── daily_pick_20260605_swing.txt    # 完整报告正文，人工阅读用
│   └── 07/
└── 2027/
```

推荐每日 crontab 自动存档，积累数据后用于：
- 回溯历史选股表现
- 优化打分权重
- 验证策略有效性
- 分析新闻/财报因子的预测能力

## Sub-agent

| Agent | 文件 | 用途 |
|---|---|---|
| stock_deep_evaluator | `agents/stock-team/stock_deep_evaluator.md` | 单股深度分析、买卖持建议、多股对比 |
| market_environment | `agents/stock-team/market_environment.md` | 大盘环境、仓位、板块轮动 |
| macro_policy_analyst | `agents/stock-team/macro_policy_analyst.md` | 宏观政策和行业影响分析 |

## 数据底座

默认读取原始数据库：

```text
/workspace/stock_downloader/stock_data.db
```

仓库里的 `stock_downloader/` 只管理代码，不提交数据库、venv、缓存文件。`.gitignore` 已排除这些文件。

## 回测指标

2023-01-03 ~ 2026-06-05：

- 年化收益：15.45%
- 最大回撤：-13.84%
- 胜率：44.2%

详见 `backtest/README.md` 和 `skills/a-stock-advisor/reference/backtest_summary.md`。

## 维护原则

- 以本仓库为单一来源，opencode 配置目录只放软链。
- 不修改 `/workspace/stock_downloader` 原始目录；需要 Git 管理的内容放本仓库。
- 不提交 `stock_data.db`、venv、缓存、API Key。
- 修改 skill/agent 后运行 `./scripts/install_opencode.sh` 并重启 opencode。

## 验证

```bash
/workspace/stock_downloader/venv/bin/python -m py_compile \
  skills/a-stock-advisor/scripts/daily_pick.py \
  skills/a-stock-advisor/scripts/evaluate_stock.py \
  skills/a-stock-advisor/scripts/lib/*.py \
  skills/tavily-search/scripts/tavily_search.py

/workspace/stock_downloader/venv/bin/python \
  skills/a-stock-advisor/scripts/daily_pick.py --fast --json >/tmp/swing_fast.json

/workspace/stock_downloader/venv/bin/python \
  skills/a-stock-advisor/scripts/daily_pick.py --mode short --fast --json >/tmp/short_fast.json
```

## 免责声明

本系统仅供学习和辅助决策，不保证收益，不构成投资建议。股市有风险，投资需谨慎。
