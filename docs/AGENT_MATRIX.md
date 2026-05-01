# Agent矩阵 - 完整Agent列表

> 所有Agent必须在 `agents/` 目录下按照分类创建
> 每个Agent需要实现 `analyze()` 方法并返回标准化的 `Signal` 对象

---

## 感知层（Perception） - 数据获取Agent

> 负责从各种数据源获取原始数据，供研究层使用

| Agent名称 | 目录 | 职责 | 数据源 |
|-----------|------|------|--------|
| 行情数据Agent | `perception/market_data/` | K线、分时、成交量 | 腾讯自选股/东方财富 |
| 财报数据Agent | `perception/financial_data/` | 三大表、科目明细 | 东方财富/巨潮 |
| 资金流向Agent | `perception/fund_flow/` | 超大单/大单/中单/小单 | 东方财富 |
| 龙虎榜Agent | `perception/lhb/` | 营业部交易明细 | 东方财富 |
| 新闻资讯Agent | `perception/news/` | 财经新闻、公告 | 新浪/财联社 |
| 公告爬虫Agent | `perception/announcement/` | 交易所公告原文 | 巨潮/交易所 |
| 宏观数据Agent | `perception/macro/` | GDP、CPI、利率等 | 国家统计局/美联储 |
| 产业链数据Agent | `perception/industry_chain/` | 上下游价格、供需 | 行业协会/Wind |
| 舆情监控Agent | `perception/sentiment/` | 社交媒体情绪 | 微博/雪球/东方财富股吧 |

---

## 研究层（Research） - 信号生成Agent

> 负责从数据中提取信号，输出结构化的Signal对象

### 📊 财报分析系列

| Agent名称 | 目录 | 职责 | 输出信号 |
|-----------|------|------|----------|
| 现金流验证Agent | `research/financial/cash_flow/` | 经营现金流vs净利润对比 | 现金流质量评级 |
| 营运资金Agent | `research/financial/working_capital/` | 应收账款、存货、预付款分析 | 营运资金健康度 |
| 合同负债Agent | `research/financial/contract_liability/` | 合同负债增长趋势 | 订单/需求信号 |
| 资本开支Agent | `research/financial/capex/` | 在建工程、固定资产变化 | 扩张信号 |
| 盈利能力Agent | `research/financial/profitability/` | 毛利率、净利率、ROE | 盈利质量评级 |
| 负债风险Agent | `research/financial/debt/` | 有息负债、杠杆率分析 | 债务风险评级 |
| 股东回报Agent | `research/financial/shareholder/` | 分红、回购、EPS | 股东回报信号 |
| 业绩预告Agent | `research/financial/forecast/` | 业绩预告解读 | 业绩预期修正 |

### 📈 趋势识别系列

| Agent名称 | 目录 | 职责 | 输出信号 |
|-----------|------|------|----------|
| 均线趋势Agent | `research/technical/ma_trend/` | MA/EMA趋势判定 | 趋势方向信号 |
| MACD信号Agent | `research/technical/macd/` | MACD金叉死叉 | 动量信号 |
| RSI超买超卖Agent | `research/technical/rsi/` | RSI数值分析 | 超买超卖信号 |
| 成交量异动Agent | `research/technical/volume/` | 放量缩量分析 | 量价配合信号 |
| 趋势强度Agent | `research/technical/trend_strength/` | ADX等趋势强度指标 | 趋势确认信号 |
| 支撑压力Agent | `research/technical/support_resistance/` | 支撑位/压力位识别 | 价位信号 |
| 形态识别Agent | `research/technical/pattern/` | K线形态识别 | 形态信号 |

### 💰 资金流向系列

| Agent名称 | 目录 | 职责 | 输出信号 |
|-----------|------|------|----------|
| 主力净流入Agent | `research/fundflow/main_force/` | 主力资金净额追踪 | 主力动向信号 |
| 连续净流入Agent | `research/fundflow/continuous/` | N日连续净流入检测 | 资金趋势信号 |
| 超大单流向Agent | `research/fundflow/block_trade/` | 超大单资金分析 | 大资金信号 |
| 散户比例Agent | `research/fundflow/retail/` | 散户vs机构资金对比 | 筹码分布信号 |
| 北向资金Agent | `research/fundflow/north_bound/` | 沪深港通北向资金 | 外资动向信号 |

### 📉 估值分析系列

| Agent名称 | 目录 | 职责 | 输出信号 |
|-----------|------|------|----------|
| PE估值Agent | `research/valuation/pe/` | 市盈率历史分位 | 估值高低信号 |
| PB估值Agent | `research/valuation/pb/` | 市净率历史分位 | 估值高低信号 |
| PS估值Agent | `research/valuation/ps/` | 市销率分析 | 估值高低信号 |
| PEG成长Agent | `research/valuation/peg/` | 盈利增速匹配度 | 成长性信号 |
| 估值切换Agent | `research/valuation/cycle/` | 行业估值轮动 | 估值切换信号 |

### 🌍 地缘宏观系列

| Agent名称 | 目录 | 职责 | 输出信号 |
|-----------|------|------|----------|
| 美联储政策Agent | `research/macro/fed_policy/` | 美联储利率决议解读 | 宏观政策信号 |
| 国内政策Agent | `research/macro/cn_policy/` | 国内政策文件解读 | 政策影响信号 |
| 地缘事件Agent | `research/macro/geopolitics/` | 国际事件影响评估 | 地缘风险信号 |
| 汇率监控Agent | `research/macro/fx/` | 美元/人民币汇率 | 汇率影响信号 |
| 通胀预期Agent | `research/macro/inflation/` | CPI/PPI分析 | 通胀信号 |

### 🏭 行业比较系列

| Agent名称 | 目录 | 职责 | 输出信号 |
|-----------|------|------|----------|
| 行业对比Agent | `research/industry/compare/` | 同行业公司对比 | 相对价值信号 |
| 行业轮动Agent | `research/industry/rotation/` | 行业强弱分析 | 行业轮动信号 |
| 产业链上下游Agent | `research/industry/chain/` | 上下游联动分析 | 产业链信号 |
| 竞争格局Agent | `research/industry/competition/` | 市场份额变化 | 竞争地位信号 |

### 📰 新闻舆情系列

| Agent名称 | 目录 | 职责 | 输出信号 |
|-----------|------|------|----------|
| 新闻情感Agent | `research/news/sentiment/` | 新闻情感分类 | 情感信号 |
| 公告解读Agent | `research/news/announcement/` | 重要公告影响评估 | 事件信号 |
| 研报摘要Agent | `research/news/research_report/` | 券商研报关键点提取 | 机构观点信号 |
| 热点追踪Agent | `research/news/hot_topic/` | 市场热点话题追踪 | 热点信号 |

### 👥 股东筹码系列

| Agent名称 | 目录 | 职责 | 输出信号 |
|-----------|------|------|----------|
| 股东结构Agent | `research/shareholder/structure/` | 股东人数变化 | 筹码集中度信号 |
| 机构持仓Agent | `research/shareholder/institution/` | 机构持仓变动 | 机构动向信号 |
| 筹码成本Agent | `research/shareholder/chip/` | 筹码分布分析 | 成本区间信号 |

### ⚠️ 风险预警系列

| Agent名称 | 目录 | 职责 | 输出信号 |
|-----------|------|------|----------|
| 财务异常Agent | `research/risk/financial_anomaly/` | 财报异常检测 | 财务风险信号 |
| 商誉减值Agent | `research/risk/goodwill/` | 商誉减值风险 | 商誉风险信号 |
| 股权质押Agent | `research/risk/pledge/` | 股权质押比例 | 质押风险信号 |
| 解禁压力Agent | `research/risk/unlock/` | 限售股解禁 | 减持压力信号 |
| 诉讼风险Agent | `research/risk/litigation/` | 重大诉讼检测 | 法律风险信号 |

---

## 风控层（Risk） - 风险管理Agent

| Agent名称 | 目录 | 职责 |
|-----------|------|------|
| 仓位管理Agent | `risk/position/` | 根据信号强度和风险计算仓位 |
| 止损监控Agent | `risk/stop_loss/` | 动态止损线监控 |
| 最大回撤Agent | `risk/max_drawdown/` | 回撤控制 |
| 流动性检查Agent | `risk/liquidity/` | 持仓流动性评估 |
| 黑天鹅预警Agent | `risk/black_swan/` | 极端风险事件预警 |
| 集中度风险Agent | `risk/concentration/` | 单票/单行业集中度控制 |

---

## 认知层（Cognition） - 推理链生成Agent

| Agent名称 | 目录 | 职责 |
|-----------|------|------|
| 推理链生成Agent | `cognition/reasoning/` | 生成完整决策推理链 |
| 风险解读Agent | `cognition/risk_narrative/` | 风险提示的通俗解读 |
| 投资逻辑Agent | `cognition/investment_logic/` | 总结投资逻辑 |
| 学习笔记Agent | `cognition/learning/` | 生成学习要点笔记 |

---

## Agent开发优先级

### 第一批（核心，必做）

| 优先级 | Agent | 原因 |
|--------|-------|------|
| P0 | 行情数据Agent | 所有分析的基础 |
| P0 | 财报数据Agent | 财报分析的基础 |
| P0 | 现金流验证Agent | 八步框架第一步 |
| P0 | 合同负债Agent | 核心信号源 |
| P0 | 趋势识别Agent | 技术面基础 |
| P0 | 主力净流入Agent | 资金面基础 |
| P1 | 估值Agent | PE/PB分位 |
| P1 | 仓位管理Agent | 风控核心 |

### 第二批（重要，扩展）

| 优先级 | Agent | 原因 |
|--------|-------|------|
| P1 | 营运资金Agent | 验证财报质量 |
| P1 | 资本开支Agent | 判断扩张周期 |
| P1 | 新闻情感Agent | 捕捉突发事件 |
| P1 | 地缘事件Agent | 宏观风险 |
| P2 | 北向资金Agent | 外资动向 |
| P2 | 龙虎榜Agent | 主力行为 |
| P2 | 行业轮动Agent | 赛道选择 |

### 第三批（完善，优化）

| 优先级 | Agent | 原因 |
|--------|-------|------|
| P2 | 股东结构Agent | 筹码分布 |
| P2 | 研报摘要Agent | 机构观点 |
| P2 | 黑天鹅预警Agent | 极端风险 |
| P3 | 产业链Agent | 深度研究 |
| P3 | 形态识别Agent | 精细化技术 |

---

## Agent命名规范

```
agents/
├── [分类]/
│   ├── __init__.py
│   ├── config.py      # 配置文件
│   ├── agent.py       # 核心逻辑
│   ├── data_source.py # 数据源（可选）
│   └── test.py        # 测试（可选）
```

## Agent返回值示例

```python
from agents.signal import Signal, bullish_signal

# 方式1：直接创建Signal对象
signal = Signal(
    direction="bullish",
    confidence=0.85,
    reasoning="Q3合同负债同比增长200%，显示下游需求旺盛",
    signals=["合同负债+200%", "经营现金流反超净利润"],
    source="现金流验证Agent",
    signal_type="financial",
    stock_code="688521",
    weight=1.0,
    meta={"quarter": "Q3", "year": 2024}
)

# 方式2：使用便捷函数
signal = bullish_signal(
    confidence=0.85,
    reasoning="...",
    signals=["信号1", "信号2"],
    source="合同负债Agent",
    stock_code="688521",
    meta={"growth_rate": 2.0}
)
```

---

*最后更新：2026-05-01*
