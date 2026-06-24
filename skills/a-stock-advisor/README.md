# A-Stock Advisor (opencode skill)

基于本地 A 股数据库（行情/财务/技术指标/政策）的选股和评估 skill。

## 核心能力

1. **每日选股** - 默认中期波段（1~3个月，目标15~25%），先量化初筛30只，再财报硬筛、联网新闻/公告验证、综合重排，输出5只候选；支持 `--mode short` 短线模式
2. **单股评估** - 6 维度打分输出"买/观望/回避"建议

## 性能指标（2023-2026 回测）

- 年化收益: **15.45%**
- 最大回撤: -13.84%
- 胜率: 44.2%
- 跑赢沪深 300 约 9% 年化

详见 [`reference/backtest_summary.md`](reference/backtest_summary.md)。

## 使用方法

### 在 opencode 对话中
直接说：
- "今天选什么"
- "评估一下 600519"
- "300394 现在能买吗"

skill 会自动加载并调用对应脚本。

### 命令行
```bash
cd scripts

# 每日选股（默认中期波段 + 财报筛选 + 联网新闻验证）
python daily_pick.py

# 快速模式：跳过联网新闻验证
python daily_pick.py --fast

# 短线模式（2~4周）
python daily_pick.py --mode short

# 评估单股
python evaluate_stock.py 600519.SH
python evaluate_stock.py 600519        # 也支持

# JSON 输出
python daily_pick.py --json
python evaluate_stock.py 600519 --json
```

## 依赖

- Python 3.10+
- pandas, numpy
- SQLite 数据库（由 [`stock_downloader`](../../stock_downloader/) 模块下载）
- Tavily API Key（默认联网新闻/公告验证需要；也可用 `--fast` 跳过）
- 本仓库 vendored 的 `../tavily-search/scripts/tavily_search.py`

## 安装

```bash
# 1. 克隆整个项目
git clone https://github.com/<your-org>/a-stock-system.git ~/code/a-stock-system

# 2. 装数据下载器依赖
cd ~/code/a-stock-system/stock_downloader
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. 配 Tushare token
cp .env.example .env
# 编辑 .env, 填写 TUSHARE_TOKEN

# 4. 下载数据（首次约 2 小时）
./run.sh

# 5. 安装 opencode skills 和 agents
cd ~/code/a-stock-system
./scripts/install_opencode.sh

# 6. 编辑 ~/.opencode/.env，填写 TAVILY_API_KEY

# 7. 重启 opencode
```

## 文件结构

```
a-stock-advisor/
├── SKILL.md              # opencode skill 入口
├── README.md             # 本文件
├── config.example.env    # 环境变量样例
├── scripts/
│   ├── daily_pick.py
│   ├── evaluate_stock.py
│   └── lib/
│       ├── financials.py
│       ├── news_verifier.py
│       └── strategy.py
└── reference/
    ├── mindset_v2.md     # 方法论摘要
    └── backtest_summary.md
```

## 相关 subagent

- `stock_deep_evaluator` - 深度评估单股（财务 + 政策 + 资金面）
- `market_environment` - 大盘环境分析

均位于 `~/.config/opencode/agents/stock-team/`

## 免责声明

本工具仅供学习和辅助决策，**不保证收益，不构成投资建议**。股市有风险，投资需谨慎。

## License

MIT
