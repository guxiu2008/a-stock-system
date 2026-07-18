---
name: a-stock-advisor
description: A股选股和评估助手 - 三合一 Checklist 输出。支持三种评估模式：短线策略、单股深度、中线策略，自动输出到日期文件夹。
---

# A 股选股与评估助手

基于本地 A 股数据库执行每日选股和单股评估。**核心特性：三合一 Checklist 输出，自动按日期归档。**

---

## 何时使用此 skill

**自动触发：**
- "评估 600519" / "看看 300750 怎么样"
- "今天选股" / "每日选股"
- "短线分析 002594" / "中线分析 601318"
- 用户给出股票代码

**不要触发：** 美股/港股/加密货币、非投资问题。

---

## 核心功能

### 🎯 默认模式：三合一综合评估

对单只股票同时输出 **三份 Checklist**，覆盖短线、波段、中线三个维度：

```bash
cd ${A_STOCK_SKILL_DIR:-skills/a-stock-advisor}/scripts
python evaluate_stock.py 600519.SH
```

**输出三份文件：**
```
output/
└── 20250625/              ← 自动按日期归档
    ├── 600519.SH_short_143022.md    ← 短线策略清单
    ├── 600519.SH_swing_143022.md    ← 单股深度评估清单
    └── 600519.SH_growth_143022.md   ← 中线策略清单
```

每份 Checklist 都是标准 markdown 格式，带 ✅/❌/⚠️ 标记。

---

### ⚡ 单模式输出

如果只需要某一个维度：

| 模式 | 命令 | 对应清单 |
|------|------|---------|
| 短线 | `python evaluate_stock.py 002594.SZ --mode short` | 快进快出清单 |
| 波段 | `python evaluate_stock.py 600519.SH --mode swing` | 六维打分清单 |
| 中线 | `python evaluate_stock.py 601318.SH --mode growth` | 价值成长清单 |

---

### 🎯 每日选股

```bash
cd ${A_STOCK_SKILL_DIR:-skills/a-stock-advisor}/scripts
python daily_pick.py --mode swing
```

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `STOCK_DB_PATH` | `/workspace/stock_downloader/stock_data.db` | SQLite 数据库路径 |
| `CHECKLIST_OUTPUT_DIR` | `./output/{date}` | Checklist 输出目录<br>支持变量：`{date}`=YYYYMMDD, `{ts}`=HHMMSS |

用法示例：
```bash
export CHECKLIST_OUTPUT_DIR="/data/stock_reports/{date}"
python evaluate_stock.py 600519.SH
```

---

## 架构说明

所有计算逻辑和输出逻辑都已移到 `lib/` 目录，入口脚本非常精简：

```
scripts/
├── evaluate_stock.py           94行 → 只做流程编排，无计算逻辑
└── lib/
    ├── checklist_output.py     通用 Checklist 输出引擎（格式化、文件保存）
    ├── stock_evaluator.py      单股评估核心（三份 Checklist 共享计算）
    └── ... 其他基础库
```

---

## 代码支持

代码支持：`600519.SH` / `600519` / 名称。若用户给名称，先查数据库：
```bash
sqlite3 ${STOCK_DB_PATH:-/workspace/stock_downloader/stock_data.db} \
  "SELECT ts_code, name FROM dim_stock_info WHERE name LIKE '%名称%' LIMIT 5"
```

---

> [免责声明] 本工具仅供参考，不构成投资建议。请严格执行你的交易纪律。
