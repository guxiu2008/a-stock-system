# 📈 中国 A 股短线/波段投资：思维模型与工程化指南 (2026 版 v2)

> **v2 修正版** · 上一版（v1）在板块筛选、止损规则和目标收益上有几个硬伤，本版已重写。
> 历史版本备份在 `mindset.md.v1.backup` 和 `mindset.md.backup`。
> v2 核心理念：**先判大盘 → 数据优先 → 3 日趋势 → 中位段选股 → 技术面确认 → 风险收益比 ≥ 2:1 → 严格止损**

> **核心原则：** 在 A 股市场，获利的关键在于博弈"政策赔率"与"财务确定性"，并配合资金趋势和严格风控。本手册旨在将职业投资者的"非对称思维"转化为可供 Agent 执行的逻辑框架。

---

## 一、 五大核心思维模型

### 1. 政策北极星思维 (Policy-Driven Logic)
* **认知：** A 股是高度受宏观政策驱动的市场。国家战略的投向即是资本长期增值的方向。
* **行动：** 将政策文件（如"十五五"规划）视为长线布局的"地图"。
* **Agent 逻辑：** 通过 `macro_policy_scrapper.py` 监控关键词频率。如果"新质生产力"或"自主可控"在核心官媒中出现的频次跨越式增长，则视为大级别行情的起点。

### 2. 周期蛰伏思维 (Cycle Patience)
* **认知：** 波动是 A 股的常态。70% 的涨幅往往集中在 10% 的极短时间内，其余时间都在等待。
* **行动：** 拒绝频繁调仓，用"3 个月周期"视角审视"3 天波动"。
* **Agent 逻辑：** 利用 `market_quota_syncer.py` 计算标的的"位置感"。在估值历史低位且基本面未恶化时，Agent 应建议"蹲守"而非"止损"。

### 3. 杠铃策略模型 (Barbell Strategy)
* **认知：** 在不确定性中通过极端配置锁定风险。
* **配置建议：**
    * **左端（防御）：** 高股息、稳定现金流的"现金牛"（如电力、大型银行）。要求：股息率 > 5%。
    * **右端（进攻）：** 具备全球竞争力的"硬科技成长"（如 AI 硬件出海、半导体核心资产）。
* **Agent 逻辑：** 结合 `dividend_yield_tracker.py` 锁定左端底仓，为进攻端争取时间。

### 4. 逆向拥挤度博弈 (Anti-Crowding Sentiment)
* **认知：** 当全市场达成"共识"时，风险往往最大。
* **监控信号：** 融资余额激增而股价滞涨，意味着筹码极度不稳，容易发生踩踏。
* **Agent 逻辑：** 利用 `money_flow_analyst.py` 监控个股融资占比。当拥挤度超过历史 90% 分位时，触发风险预警。

### 5. 财务护城河三问 (Fundamental Moat)
* **认知：** 长期收益最终必须由利润驱动，而非"讲故事"。
* **硬核指标：**
    1.  **ROE 稳定性：** 过去 5 年加权平均 ROE 是否持续高于 15%？
    2.  **现金流含金量：** 经营性现金流净额是否覆盖净利润？
    3.  **定价权：** 毛利率是否能在成本波动的环境下保持稳定？
* **Agent 逻辑：** 通过 `fundamental_master.py` 自动过滤掉报表虚假的资产。

---

## 二、 投资者行为对比表

| 维度 | 顶级思维 (长期获利)       |
| :--- |:------------------|
| **关注点** | 行业竞争格局、政策北极星      |
| **交易频率** |  极低频，布局未来 24-36 个月|
| **对待亏损** |  承认错误，或在优质打折资产上加仓 |
| **风险控制** |  杠铃配置，基于规则自动触发 |

---

## 三、 OpenClaw Agent 工具矩阵架构

为了将上述思维落地，你的 Agent 需要协同调用以下 6 个核心工具模块：

1.  **`asset_registry.py`**：建立全市场地图，区分行业与概念。
2.  **`market_quota_syncer.py`**：同步复权行情，识别价格周期。
3.  **`fundamental_master.py`**：深挖财务护城河，执行"三问"逻辑。
4.  **`dividend_yield_tracker.py`**：监控红利收益，构筑杠铃左端防御。
5.  **`money_flow_analyst.py`**：分析资金流向，规避情绪拥挤风险。
6.  **`macro_policy_scrapper.py`**：捕捉政策风向，指明长期投资航向。

---

## 四、 投资金句（写入 Agent Prompt 参考）
> "买入那些国家需要它存在、且它能持续产生现金流的公司。时间是好公司的朋友，是坏公司的敌人。"

---

## 五、 短线/波段分析框架（7步法 · v2 修正版）

> **v1 → v2 关键修正：**
> 1. 加入"第 0 步：大盘环境判断"。大盘下跌趋势中所有策略都失效，必须先判断环境。
> 2. 板块筛选从"昨日单日涨幅"改为"近 3 日累计涨幅 + 持续性"。单日数据是噪声。
> 3. 个股筛选从"取板块涨幅前 20"改为"取板块内涨幅 30%~70% 分位"。头部往往是接盘区。
> 4. 止损从"固定 -3%"改为"跌破 MA20 或买入逻辑被证伪"。固定百分比在震荡市会反复挨打。
> 5. 目标收益修正为合理区间，年化目标 15~25%（而非 50%+）。

### 0. 第零步：大盘环境判断（决定仓位上限）

```sql
SELECT ts_code, trade_date, close, ma5, ma10, ma20, ma60,
       CASE
           WHEN close > ma20 AND ma5 > ma10 THEN '上升趋势'
           WHEN close < ma20 AND ma5 < ma10 THEN '下跌趋势'
           ELSE '震荡市'
       END as trend_status
FROM market_indicators
WHERE ts_code IN ('000001.SH','399001.SZ','399006.SZ')
  AND trade_date = (SELECT MAX(trade_date) FROM market_indicators
                    WHERE ts_code = '000001.SH')
ORDER BY ts_code;
```

| 大盘状态 | 判定条件 | 建议仓位 | 单票上限 |
|---------|---------|---------|---------|
| 上升趋势 | 上证 > MA20 且 MA5 > MA10 > MA20 | 60~80% | 20% |
| 震荡市   | 上证在 MA20 上下 ±3% 缠绕      | 30~50% | 15% |
| 下跌趋势 | 上证 < MA20 且 MA5 < MA10      | 10~20% 或空仓 | 10% |

**下跌趋势中只做超跌反弹，不追涨。**

### 1.1 全维度信息收集
| 维度 | 信息来源 |
|------|---------|
| 新闻 | 昨晚到今早政策、产业、外围消息 |
| 政策 | 央行、证监会、部委最新动向 |
| 数据 | 昨天盘面行业/概念/个股表现 |
| 宏观 | PMI、CPI、社融、外汇 |
| 基本面 | 业绩预告、估值、盈利预测 |
| 资金面 | 北向资金、主力流向、融资融券 |
| 技术面 | 关键均线、量价、K线形态 |

### 1.2 新闻与数据碰撞
- 一致信号：新闻说的 ↔ 数据验证了（最强）
- 分歧点：新闻说涨但数据没验证（观望，可能是骗局）
- 预期差：市场没注意到但很重要的信息（最大的机会）
- **警惕利好兑现**：连续 3 天大涨后出利好 ≈ 出货信号

### 1.3 趋势判断（看 3~5 日，不看单日）
- 当前阶段：底部蛰伏 / 启动初期 / 主升浪 / 高位震荡 / 下跌
- 持续性：单日异动还是趋势形成
- **判断标准：连续 3 天中至少 2 天收阳，且量能温和放大 = 趋势确认**

### 1.4 风险收益分析
- 上行空间：到下一个压力位多少幅度？
- 下行风险：到下一个支撑位（如 MA20/MA60）跌多少？
- **风险收益比要求：上行/下行 >= 2:1，否则不动**
- 胜率：基于历史类似形态，是 60% 还是 30%？

### 1.5 操作建议
- 买什么：具体个股（代码+名称）
- 何时买：开盘/盘中/尾盘
- 何时卖：止盈位+止损位
- 持有周期：半月/1月/3月/半年/1年
- 预期收益：保守/中性/乐观

### 1.6 验证与迭代
- 每日复盘
- 修正框架

---

## 六、 操作原则（v2 修正版）

### 选股条件（更新）
1. **排除新股**（上市 < 1 年），排除 ST/*ST
2. **要求有分红记录**（>= 1 次，剔除壳股和长期亏损股）
3. **基本面底线**：最近一期 ROE > 10%，资产负债率 < 70%（金融除外）
4. **行业符合最近政策方向**或处于景气度上行（参考 macro_policy 数据）
5. **技术面同时满足以下 4 条中至少 3 条：**
   - 股价站上 MA20
   - MACD > 0 或 MACD_hist 由负转正（零轴附近金叉，**拒绝高位金叉**）
   - KDJ_J 在 20~80 之间（**非超买**）
   - 近 5 日成交量 > 前 20 日均量 * 1.2（**放量确认**）
6. **流通市值** > 30 亿（剔除流动性差的小票，方便进出）

### 推荐原则
- **只在有明显机会时推荐**，宁可不推也不乱推
- 大盘下跌趋势中，每天最多推 1 只（且仅限超跌反弹）
- 震荡市每天最多推 2 只
- 上升趋势中每天最多推 3 只
- **预期收益按时间维度分层（修正后，更现实）：**
  - 半月：2~3%（保守目标）
  - 1 个月：3~5%（正常目标）
  - 3 个月：8~12%（乐观目标）
  - 半年：15~20%
  - 1 年：**15~25%**（年化目标，对标公募前 10%）

> ⚠️ **关于"年化 50%+"的诚实说明：** 这不是可复制的目标。公募基金长期年化前 1% 大约 20~30%，私募头部量化也就 15~25%。
> 我们的目标是：**跑赢沪深 300（年化 8~15%），最大回撤 < 15%，长期复利**。
> 偶尔某一年踩对赛道做到 50%+ 完全可能，但**不能作为系统目标**，否则会被迫加杠杆/追高，最终大亏。

### 选股流程（每日执行，v2 版）

**第零步：判断大盘环境** → 决定今日仓位上限和最多推荐数

**第一步：筛选 3 日强势板块**
1. 计算近 3 日行业平均涨幅排名（取前 15）
2. 过滤：3 日内至少 2 天收涨（持续性确认）
3. 排除：3 日累计涨幅 > 15% 的过热板块（追高风险）
4. 计算近 3 日概念涨幅排名（取前 15）
5. 取行业与概念**排名 3~12 名的交集**（避开头部最热的，往往是接盘区）

**第二步：板块内筛选个股**
1. 排除新股、ST
2. 保留有分红记录的股票
3. 取板块内**近 3 日涨幅在 30%~70% 分位**的个股（中间段，非最高也非最低）
4. ROE > 10%，流通市值 > 30 亿

**第三步：技术面确认买点**
1. 检查 MA20/MACD/KDJ/RSI/BOLL/成交量
2. 满足至少 3 条买入条件
3. 计算上行空间 / 下行空间 >= 2:1

**第四步：确定具体标的**
1. 综合得分前 2~3 只
2. 给出建议买入区间、目标价、止损位、预期持有期
3. 给出明确的"今日操作建议"（买/观望/暂不动）

### 报价模板（每日填写，v2 版）

推荐个股需包含以下信息：

```
| 代码 | 名称 | 行业 | 昨日收盘 | 建议买入区间 | 目标价(+8%) | 止损位 | 预期持有期 | 风险收益比 |
|------|------|------|---------|------------|------------|--------|----------|----------|
| 300394.SZ | 天孚通信 | 通信设备 | 333.33 | 320~330 | 360 | 跌破MA20或310(-7%) | 2~4周 | 2.3:1 |
```

**说明：**
- 建议买入区间：以最近 5 日均价或 MA20 为锚，下浮 2~3% 为低吸点
- 目标价：取近 30 日压力位或 +8~12%（不要贪心）
- 止损位：跌破 MA20 或买入价 -7%（取较高者，避免被洗）
- 预期持有期：明确告知，到期未达目标需重审逻辑

### 买入时机判断
- 高开 > 5%：**不追**，等盘中回调到 MA5/MA10 再考虑
- 高开 2~5%：可盘中等回踩均线买入
- 平盘或低开：**最佳买点**，分两笔买入（开盘 50% + 收盘前 50%）

### 卖出时机判断（v2 修正）
- **达到目标价**：分批卖出，先卖 50%，剩余看势头（止盈不止损浮盈）
- **MACD 顶背离 + 放量滞涨**：直接清仓
- **板块龙头跌停或负面消息**：同板块全部减仓
- **收盘跌破 MA20**：减仓 50%；连续 2 天跌破 → 全部止损
- **跌破买入价 -7%**：无条件止损（取代旧的 -3%，避免被洗）
- **持有 20 个交易日未达预期**：重新审视逻辑，不符合就退出

---

## 七、 每日分析工具使用手册

### 准备工作：获取最新交易日期
```bash
# 获取数据库中最新交易日
sqlite3 stock_data.db "SELECT MAX(trade_date) FROM fact_daily_quotes"
```

### 第一步：获取近期盘面数据（v2：用 3 日聚合代替单日）

#### 1.1 近 3 日行业涨幅排名
```sql
-- v2: 用近 3 个交易日的累计涨幅而非单日，更能反映趋势
WITH latest_dates AS (
    SELECT DISTINCT trade_date FROM fact_daily_quotes
    ORDER BY trade_date DESC LIMIT 3
)
SELECT s.industry,
       COUNT(DISTINCT q.trade_date) as days_count,
       ROUND(AVG(q.pct_chg), 2) as avg_pct,
       SUM(CASE WHEN q.pct_chg > 0 THEN 1 ELSE 0 END) as positive_days
FROM fact_daily_quotes q
JOIN dim_stock_info s ON q.ts_code = s.ts_code
WHERE q.trade_date IN (SELECT trade_date FROM latest_dates)
  AND s.industry IS NOT NULL AND s.industry != ''
GROUP BY s.industry
HAVING days_count >= 3 AND positive_days >= 2  -- 持续性确认
ORDER BY avg_pct DESC LIMIT 15;
```

#### 1.2 近 3 日概念涨幅排名
```sql
WITH latest_dates AS (
    SELECT DISTINCT trade_date FROM fact_daily_quotes
    ORDER BY trade_date DESC LIMIT 3
)
SELECT m.concept_name,
       COUNT(DISTINCT m.ts_code) as stock_count,
       ROUND(AVG(q.pct_chg), 2) as avg_pct
FROM map_concept_stock m
JOIN fact_daily_quotes q ON m.ts_code = q.ts_code
WHERE q.trade_date IN (SELECT trade_date FROM latest_dates)
GROUP BY m.concept_name
HAVING stock_count >= 5  -- 排除冷门小概念
ORDER BY avg_pct DESC LIMIT 15;
```

#### 1.3 板块内个股涨幅分布（用于按分位选股）
```sql
-- 给定行业，列出近 3 日累计涨幅，并标记分位
WITH latest_dates AS (
    SELECT DISTINCT trade_date FROM fact_daily_quotes
    ORDER BY trade_date DESC LIMIT 3
),
stock_perf AS (
    SELECT q.ts_code, s.name, s.industry,
           ROUND(SUM(q.pct_chg), 2) as cum_3d_pct,
           MAX(q.close) as latest_close
    FROM fact_daily_quotes q
    JOIN dim_stock_info s ON q.ts_code = s.ts_code
    WHERE q.trade_date IN (SELECT trade_date FROM latest_dates)
      AND s.industry = '【替换为目标行业】'
      AND s.name NOT LIKE '%ST%'
      AND s.list_date < date('now', '-365 days')
    GROUP BY q.ts_code
)
SELECT *, NTILE(10) OVER (ORDER BY cum_3d_pct DESC) as decile
FROM stock_perf
ORDER BY cum_3d_pct DESC;
-- 选股时取 decile BETWEEN 3 AND 7（中间 40% 分位）
```

#### 1.4 大盘指数情况 + 趋势判断
```sql
-- 大盘最新点位 + 均线（用于第零步判断）
SELECT i.ts_code, i.trade_date, i.close, i.pct_chg,
       mi.ma5, mi.ma10, mi.ma20, mi.ma60,
       CASE
           WHEN i.close > mi.ma20 AND mi.ma5 > mi.ma10 THEN '上升趋势'
           WHEN i.close < mi.ma20 AND mi.ma5 < mi.ma10 THEN '下跌趋势'
           ELSE '震荡市'
       END as trend_status
FROM fact_index_daily i
LEFT JOIN market_indicators mi ON i.ts_code = mi.ts_code AND i.trade_date = mi.trade_date
WHERE i.trade_date = (SELECT MAX(trade_date) FROM fact_index_daily)
  AND i.ts_code IN ('000001.SH','399001.SZ','399006.SZ');
```

---

### 第二步：资金流向分析（核心步骤）

#### 2.1 板块持续性分析
```bash
# 比较昨日和前日涨幅前5行业，判断资金是否在持续买入
# 先获取昨日前5
sqlite3 stock_data.db "SELECT s.industry, AVG(q.pct_chg) as avg_pct 
FROM fact_daily_quotes q 
JOIN dim_stock_info s ON q.ts_code = s.ts_code 
WHERE q.trade_date = 'YYYYMMDD' 
GROUP BY s.industry 
ORDER BY avg_pct DESC 
LIMIT 5"

# 再获取前一日前5，看是否重叠
sqlite3 stock_data.db "SELECT s.industry, AVG(q.pct_chg) as avg_pct 
FROM fact_daily_quotes q 
JOIN dim_stock_info s ON q.ts_code = s.ts_code 
WHERE q.trade_date = 'YYYYMMDD-1' 
GROUP BY s.industry 
ORDER BY avg_pct DESC 
LIMIT 5"
```

#### 2.2 高低切换识别
```bash
# 昨日涨幅前5 vs 跌幅前5
# 如果涨幅前5的板块今天低开或下跌，说明资金在高低切换
sqlite3 stock_data.db "SELECT s.industry, AVG(q.pct_chg) as avg_pct 
FROM fact_daily_quotes q 
JOIN dim_stock_info s ON q.ts_code = s.ts_code 
WHERE q.trade_date = 'YYYYMMDD' 
GROUP BY s.industry 
ORDER BY avg_pct ASC 
LIMIT 5"
```

#### 2.3 资金是否在出货（关键信号）
```bash
# 如果某板块昨日涨幅>3%，今日大幅低开，说明可能是利好兑现出货
# 获取今日开盘价 vs 昨日收盘价
sqlite3 stock_data.db "SELECT q.ts_code, s.name, q.trade_date, q.open, q.close, 
(q.open - q.close) / q.close * 100 as gap 
FROM fact_daily_quotes q 
JOIN dim_stock_info s ON q.ts_code = s.ts_code 
WHERE q.trade_date = 'YYYYMMDD' 
AND s.industry IN ('行业1','行业2','行业3')"
```

---

### 第三步：验证新闻与数据碰撞

#### 3.1 检查新闻说的板块是否在数据中验证
```bash
# 比如新闻说半导体要涨，检查半导体板块实际表现
sqlite3 stock_data.db "SELECT s.industry, COUNT(*) as cnt, AVG(q.pct_chg) as avg_pct 
FROM fact_daily_quotes q 
JOIN dim_stock_info s ON q.ts_code = s.ts_code 
WHERE q.trade_date = 'YYYYMMDD' 
AND s.industry = '半导体' 
GROUP BY s.industry"
```

#### 3.2 检查新闻说的概念是否在数据中验证
```bash
sqlite3 stock_data.db "SELECT m.concept_name, COUNT(*) as cnt, AVG(q.pct_chg) as avg_pct 
FROM map_concept_stock m 
JOIN fact_daily_quotes q ON m.ts_code = q.ts_code 
WHERE q.trade_date = 'YYYYMMDD' 
AND m.concept_name = '人工智能' 
GROUP BY m.concept_name"
```

---

### 第四步：筛选符合选股条件的个股

#### 4.1 基础筛选（排除新股/ST）
```bash
# 排除新股（上市不足1年）和ST股
sqlite3 stock_data.db "SELECT ts_code, name, industry, list_date 
FROM dim_stock_info 
WHERE list_status = 'L' 
AND name NOT LIKE '%ST%' 
AND name NOT LIKE '%*ST%' 
AND list_date < date('now', '-365 days')"
```

#### 4.2 筛选有分红记录的股票（低风险）
```bash
# 保留至少有1次分红记录的股票
sqlite3 stock_data.db "SELECT ts_code, COUNT(*) as div_count 
FROM fact_dividend_history 
GROUP BY ts_code 
HAVING COUNT(*) >= 1"
```

#### 4.3 筛选热点板块内的股票
```bash
# 从热点板块中筛选符合条件的股票
sqlite3 stock_data.db "SELECT q.ts_code, s.name, s.industry, q.close, q.pct_chg 
FROM fact_daily_quotes q 
JOIN dim_stock_info s ON q.ts_code = s.ts_code 
WHERE q.trade_date = 'YYYYMMDD' 
AND s.industry IN ('行业1','行业2','行业3') 
AND s.name NOT LIKE '%ST%' 
AND s.list_date < '20250101' 
ORDER BY q.pct_chg DESC 
LIMIT 30"
```

#### 4.4 综合选股 SQL（一站式，v2 核心）
```sql
-- 综合：热点板块 + 非新股 + 非ST + 有分红 + 板块中位段
WITH latest_date AS (
    SELECT MAX(trade_date) as td FROM fact_daily_quotes
),
last_3d AS (
    SELECT DISTINCT trade_date FROM fact_daily_quotes
    ORDER BY trade_date DESC LIMIT 3
),
target_industries AS (
    -- 替换为第三步选出的 2~3 个行业
    SELECT '通信设备' as industry
    UNION SELECT '半导体'
    UNION SELECT '电池'
),
has_dividend AS (
    SELECT DISTINCT ts_code FROM fact_dividend_history
),
stock_cum AS (
    SELECT q.ts_code, s.name, s.industry,
           ROUND(SUM(q.pct_chg), 2) as cum_3d_pct
    FROM fact_daily_quotes q
    JOIN dim_stock_info s ON q.ts_code = s.ts_code
    JOIN target_industries ti ON s.industry = ti.industry
    JOIN has_dividend hd ON s.ts_code = hd.ts_code
    WHERE q.trade_date IN (SELECT trade_date FROM last_3d)
      AND s.name NOT LIKE '%ST%' AND s.name NOT LIKE '%*ST%'
      AND s.list_date < date('now', '-365 days')
    GROUP BY q.ts_code
)
SELECT * FROM (
    SELECT *, NTILE(10) OVER (ORDER BY cum_3d_pct DESC) as decile
    FROM stock_cum
) ranked
WHERE decile BETWEEN 3 AND 7  -- 中间分位，避开过热和滞涨
  AND cum_3d_pct > 0
ORDER BY cum_3d_pct DESC;
```

---

### 第五步：技术面确认买点（v2 新增，关键步骤）

#### 5.1 检查个股技术指标
```sql
SELECT mi.ts_code, s.name, mi.trade_date,
       q.close,
       mi.ma5, mi.ma10, mi.ma20, mi.ma60,
       mi.macd, mi.macd_hist,
       mi.kdj_j, mi.rsi6,
       mi.boll_upper, mi.boll_mid, mi.boll_lower,
       -- 综合买入信号判断
       CASE WHEN q.close > mi.ma20 THEN 1 ELSE 0 END
       + CASE WHEN mi.macd > 0 AND mi.macd_hist > 0 THEN 1 ELSE 0 END
       + CASE WHEN mi.kdj_j BETWEEN 20 AND 80 THEN 1 ELSE 0 END
       + CASE WHEN mi.rsi6 BETWEEN 30 AND 70 THEN 1 ELSE 0 END
       + CASE WHEN q.close < mi.boll_upper THEN 1 ELSE 0 END
       as buy_signal_score
FROM market_indicators mi
JOIN dim_stock_info s ON mi.ts_code = s.ts_code
JOIN fact_daily_quotes q ON mi.ts_code = q.ts_code AND mi.trade_date = q.trade_date
WHERE mi.ts_code IN ('股票1','股票2','股票3')
  AND mi.trade_date = (SELECT MAX(trade_date) FROM market_indicators)
ORDER BY buy_signal_score DESC;
-- buy_signal_score >= 3 才考虑买入
```

#### 5.2 成交量确认（必须）
```sql
-- 近 5 日均量 vs 前 20 日均量，比值 > 1.2 视为放量
WITH vol_stat AS (
    SELECT ts_code,
           AVG(CASE WHEN rn <= 5 THEN vol END) as avg_5d_vol,
           AVG(CASE WHEN rn > 5 AND rn <= 25 THEN vol END) as avg_20d_vol
    FROM (
        SELECT ts_code, vol,
               ROW_NUMBER() OVER (PARTITION BY ts_code ORDER BY trade_date DESC) as rn
        FROM fact_daily_quotes
        WHERE trade_date >= (SELECT date(MAX(trade_date), '-40 days') FROM fact_daily_quotes)
    )
    WHERE rn <= 25
    GROUP BY ts_code
)
SELECT ts_code,
       ROUND(avg_5d_vol / avg_20d_vol, 2) as vol_ratio,
       CASE WHEN avg_5d_vol > 1.2 * avg_20d_vol THEN '放量'
            WHEN avg_5d_vol < 0.7 * avg_20d_vol THEN '缩量'
            ELSE '正常' END as vol_status
FROM vol_stat
WHERE ts_code IN ('股票1','股票2','股票3');
-- 优选"放量"的股票
```

#### 5.3 风险收益比计算
```sql
-- 近 30 日的支撑位和压力位
SELECT q.ts_code, s.name,
       MIN(q.low) as support_30d,
       MAX(q.high) as resistance_30d,
       (SELECT close FROM fact_daily_quotes
        WHERE ts_code = q.ts_code
          AND trade_date = (SELECT MAX(trade_date) FROM fact_daily_quotes)) as latest_close,
       ROUND((MAX(q.high) - (SELECT close FROM fact_daily_quotes WHERE ts_code = q.ts_code AND trade_date = (SELECT MAX(trade_date) FROM fact_daily_quotes))) /
             ((SELECT close FROM fact_daily_quotes WHERE ts_code = q.ts_code AND trade_date = (SELECT MAX(trade_date) FROM fact_daily_quotes)) - MIN(q.low)), 2) as risk_reward_ratio
FROM fact_daily_quotes q
JOIN dim_stock_info s ON q.ts_code = s.ts_code
WHERE q.ts_code IN ('股票1','股票2','股票3')
  AND q.trade_date >= date('now', '-30 days')
GROUP BY q.ts_code;
-- risk_reward_ratio >= 2 才考虑买入
```

---

### 第六步：确定具体买入/卖出价位

#### 6.1 获取推荐股票的近期价格
```sql
SELECT ts_code, trade_date, open, high, low, close, vol
FROM fact_daily_quotes
WHERE ts_code = 'XXXXXX.SZ'
  AND trade_date >= (SELECT date(MAX(trade_date), '-15 days') FROM fact_daily_quotes)
ORDER BY trade_date;
```

#### 6.2 计算建议买入区间和止损位（v2 修正）
```
基于以下规则计算（不再用固定百分比）：
- 建议买入区间：max(MA5, MA20) ~ 昨日收盘价
- 止损位：max(MA20, 买入价 * 0.93)   # 跌破 MA20 或亏 7% 取较高者
- 第一目标价：min(近30日压力位, 买入价 * 1.08)
- 第二目标价：min(近60日压力位, 买入价 * 1.15)
- 持有期：2~4 周（短线）或 1~3 月（波段）
```

---

### 第七步：每日复盘检查

#### 7.1 检查推荐股票今日表现
```sql
SELECT q.ts_code, s.name, q.close, q.pct_chg,
       mi.ma20, mi.macd, mi.macd_hist, mi.kdj_j
FROM fact_daily_quotes q
JOIN dim_stock_info s ON q.ts_code = s.ts_code
LEFT JOIN market_indicators mi ON q.ts_code = mi.ts_code AND q.trade_date = mi.trade_date
WHERE q.trade_date = (SELECT MAX(trade_date) FROM fact_daily_quotes)
  AND q.ts_code IN ('股票1','股票2','股票3');
```

#### 7.2 检查是否触发止损/止盈/调整
```
止损（触发任一立即执行）：
1. 收盘价 < MA20 连续 2 天
2. 收盘价 < 买入价 * 0.93
3. MACD 死叉且 macd_hist 由正转负
4. 买入逻辑被基本面/政策证伪

止盈（触发任一可执行）：
1. 达到第一目标价 → 卖 50%
2. 达到第二目标价 → 全部卖出
3. MACD 顶背离 + 放量滞涨 → 全部卖出
4. 持有 > 20 个交易日未达预期 → 重审逻辑
```

---

### 常用 SQL 查询速查表（v2）

```sql
-- 1. 获取最新交易日
SELECT MAX(trade_date) FROM fact_daily_quotes;

-- 2. 近 3 日行业涨幅排名（取代单日）
WITH d AS (SELECT DISTINCT trade_date FROM fact_daily_quotes ORDER BY trade_date DESC LIMIT 3)
SELECT s.industry, ROUND(AVG(q.pct_chg),2) as pct,
       SUM(CASE WHEN q.pct_chg > 0 THEN 1 ELSE 0 END) as pos_days
FROM fact_daily_quotes q JOIN dim_stock_info s ON q.ts_code = s.ts_code
WHERE q.trade_date IN (SELECT trade_date FROM d) AND s.industry IS NOT NULL
GROUP BY s.industry HAVING pos_days >= 2
ORDER BY pct DESC LIMIT 15;

-- 3. 近 3 日概念涨幅排名
WITH d AS (SELECT DISTINCT trade_date FROM fact_daily_quotes ORDER BY trade_date DESC LIMIT 3)
SELECT m.concept_name, COUNT(DISTINCT m.ts_code) as cnt, ROUND(AVG(q.pct_chg),2) as pct
FROM map_concept_stock m JOIN fact_daily_quotes q ON m.ts_code = q.ts_code
WHERE q.trade_date IN (SELECT trade_date FROM d)
GROUP BY m.concept_name HAVING cnt >= 5
ORDER BY pct DESC LIMIT 15;

-- 4. 大盘趋势判断（决定仓位）
SELECT i.ts_code, i.close, mi.ma5, mi.ma10, mi.ma20,
       CASE WHEN i.close > mi.ma20 AND mi.ma5 > mi.ma10 THEN '上升'
            WHEN i.close < mi.ma20 AND mi.ma5 < mi.ma10 THEN '下跌'
            ELSE '震荡' END as trend
FROM fact_index_daily i LEFT JOIN market_indicators mi
  ON i.ts_code = mi.ts_code AND i.trade_date = mi.trade_date
WHERE i.trade_date = (SELECT MAX(trade_date) FROM fact_index_daily)
  AND i.ts_code IN ('000001.SH','399001.SZ','399006.SZ');

-- 5. 个股技术指标 + 买入信号打分（核心）
SELECT mi.ts_code, s.name, mi.trade_date, q.close,
       mi.ma20, mi.macd, mi.macd_hist, mi.kdj_j, mi.rsi6,
       (CASE WHEN q.close > mi.ma20 THEN 1 ELSE 0 END
       + CASE WHEN mi.macd > 0 AND mi.macd_hist > 0 THEN 1 ELSE 0 END
       + CASE WHEN mi.kdj_j BETWEEN 20 AND 80 THEN 1 ELSE 0 END
       + CASE WHEN mi.rsi6 BETWEEN 30 AND 70 THEN 1 ELSE 0 END
       + CASE WHEN q.close < mi.boll_upper THEN 1 ELSE 0 END) as buy_score
FROM market_indicators mi
JOIN dim_stock_info s ON mi.ts_code = s.ts_code
JOIN fact_daily_quotes q ON mi.ts_code = q.ts_code AND mi.trade_date = q.trade_date
WHERE mi.ts_code = 'XXXXXX.SZ'
  AND mi.trade_date = (SELECT MAX(trade_date) FROM market_indicators);

-- 6. 检查是否有分红记录（剔除壳股）
SELECT ts_code, COUNT(*) as div_cnt, SUM(cash_div_tax) as total_div
FROM fact_dividend_history
WHERE ts_code = 'XXXXXX.SZ'
GROUP BY ts_code;

-- 7. 检查 ROE（基本面底线）
SELECT ts_code, end_date, roe, roe_waa, debt_to_assets, netprofit_margin
FROM fact_financial_reports
WHERE ts_code = 'XXXXXX.SZ'
ORDER BY end_date DESC LIMIT 4;

-- 8. 北向资金趋势（市场情绪）
SELECT trade_date, hsgt_net_amount, north_money
FROM fact_money_flow
WHERE trade_date >= (SELECT date(MAX(trade_date), '-10 days') FROM fact_money_flow)
ORDER BY trade_date DESC;
```

---

## 八、 分析顺序原则（v2 修正版）

### 错误顺序（v1 之前）
新闻 → 推测上涨板块 → 数据验证 → 建议

### 正确顺序（v2）
```
第零步: 大盘环境判断 (决定仓位上限)
   ↓
第一步: 近 3 日数据 (资金持续在买什么)
   ↓
第二步: 今晚新闻 (有什么催化)
   ↓
第三步: 数据 vs 新闻碰撞 (验证还是分歧)
   ↓
第四步: 板块筛选 (取行业 ∩ 概念，3~12 名)
   ↓
第五步: 个股筛选 (板块内中位段 + 基本面过线)
   ↓
第六步: 技术面确认买点 (买入信号 >= 3 分)
   ↓
第七步: 风险收益比 >= 2:1 才出手
   ↓
第八步: 给出操作建议（明确买入区间/目标/止损/持有期）
```

### 八条核心原则
1. **大盘优先**：下跌趋势中再好的票也少做或不做
2. **数据优先**：先看资金在买什么，再看新闻
3. **3 日趋势**：单日是噪声，连续 3 日才是信号
4. **不追高**：板块/个股暴涨后等回调，不追最高
5. **跟随资金**：不要预测"应该涨什么"，看"正在涨什么"
6. **警惕利好兑现**：连续大涨后出利好 ≈ 出货
7. **高低切换**：高位股开始走弱时立刻减仓
8. **纪律重于预测**：止损永远比预测重要

---

## 九、 修正历史

### v2 (2026-06) 关键修正
- ➕ 加入"第零步：大盘环境判断"
- ➕ 加入"技术面确认买点"作为独立步骤
- ➕ 加入"风险收益比 >= 2:1"硬性要求
- ➕ 加入综合买入信号打分（5 个维度）
- 🔧 板块筛选：单日涨幅 → **近 3 日累计 + 持续性**
- 🔧 个股筛选：板块涨幅前 20 → **板块内 30%~70% 分位**
- 🔧 止损：固定 -3% → **跌破 MA20 或 -7% 取较高者**
- 🔧 目标收益：年化 40%+ → **年化 15~25%（合理）**
- 🔧 每天推荐数量：根据大盘状态动态调整（1~3 只）
- 🗑️ 删除"周期蛰伏"中"3 天波动"的提法（与短线矛盾）