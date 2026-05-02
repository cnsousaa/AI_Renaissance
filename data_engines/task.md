# 职责描述

你是一位专业的金融数据资产管理大师，负责从多源、异构的量化数据获取源中抽取出统一的信息资产供下游量化 Agent 使用，让 Agent 只关心“要什么数据、怎么分析”，不关心“数据从哪来、怎么拿、怎么缓存/限频/切源/溯源”。

你的核心任务是基于当前已经明确的需求，在 `data_engines/` 目录下重新梳理并落地一套更加清晰、统一、可扩展的数据引擎方案。

---

# 已明确的关键决策

1. **工作目录统一使用 `data_engines/`**，所有方案、实现、测试、进展文档与产出结果都放在该目录下。
2. **统一返回以 `JSON-first` 为主**：
   - 面向 Agent 的正式接口优先返回结构化 `JSON`
   - `DataFrame` 仅作为内部处理实现或可选导出层，不作为统一契约的中心
3. **新方案不以 `data_providers/` 为实现基线**：
   - 不沿用旧的数据访问层结构作为默认方案
   - 不让旧的 `DataFrame-first` 设计约束新的数据引擎架构
   - `data_providers/` 最多只作为调研参考、字段口径参考与踩坑经验来源
4. **商业数据源当前阶段只做“方案级纳入与接口预留”**：
   - 例如 `Wind`、`iFinD` 需要纳入统一调研、能力模型和接口设计
   - 但当前阶段不要求完成真实适配与生产接入

---

# 核心目标

## Goal 1：完成正式数据源调研与选型框架

需要系统调研并正式纳入对比范围的数据源包括：

- 免费 / 开源 / 社区型：`AkShare`、`Tushare`、`BaoStock`
- 商业型：`Wind`、`iFinD`
- 公告 / 财报 / 行情聚合型：`巨潮 / CNInfo`、`东方财富`
- 宏观 / 统计 / 政策型：`国家统计局`、`人民银行`
- 情绪 / 热度 / 社区型：`微信指数`、`雪球`
- 研究 / 平台型：`聚宽`
- 事件型：`财经日历`
- 交易所官方接口：上交所、深交所、港交所、纽交所

调研输出不能只是罗列名字，而要明确：

1. 各数据源支持哪些数据域：量价、财报、公告 PDF、宏观、情绪、事件；
2. 各数据源覆盖哪些市场：A 股、港股、美股、指数、行业、宏观等；
3. 各数据源的更新频率、历史深度、字段质量、稳定性、授权限制、限频策略；
4. 各数据源适合用于研究、回测、生产、对照校验还是仅做接口预留；
5. 最终形成“主源 / 备源 / 对照源 / 预留源”的建议分层。

## Goal 2：设计统一的金融信息资产模型

需要设计一套优雅、简洁、统一、面向 Agent 的信息资产模型，至少覆盖：

- 量价 / 行情数据
- 财报 / 三表 / 派生指标
- 公告 PDF / 文档元数据 / 页级引用
- 宏观时间序列与事件
- 市场情绪 / 热度 / 舆情代理信号

统一模型应至少解决以下问题：

1. 如何统一描述 `Instrument`、`Dataset`、`Record`、`Document`、`Citation`、`Event`、`Sentiment`、`SourceTrace`、`QualityProfile` 等核心对象；
2. 如何统一表达抓取时间、发布时间、生效时间、观测时间、市场、交易所、币种等关键元数据；
3. 如何描述多源映射关系、字段口径差异、冲突字段优先级；
4. 如何让不同数据域都能以结构化 `JSON` 直接被 Agent 消费；
5. 如何在保留溯源能力的同时，避免把下游绑定到具体 Provider 的原始字段上。

上述核心对象在当前项目中的中文释义应明确如下：

- `Instrument`：金融标的，用于统一描述股票、指数、基金、行业主题、宏观指标对象等“被观测或被分析的主体”
- `Dataset`：数据集定义，用于标识一类稳定、可复用、可查询的数据资产集合，例如日线行情、财报三表、公告 PDF、宏观指标序列
- `Record`：数据记录，用于表示某个数据集中的最小业务数据单元，例如某只股票某一天的一条日线、某个报告期的一条财务记录
- `Document`：文档资产，用于表示公告、年报、招股书、政策文件、研究资料等原始文档及其元数据
- `Citation`：引用信息，用于表示某条结论或某段文本所对应的可追溯出处，例如某份 PDF 的页码、段落、原文位置
- `Event`：事件对象，用于表示具有明确发生时间或发布时间的事项，例如财经日历事件、政策发布、停复牌、财报披露
- `Sentiment`：情绪信号，用于表示市场情绪、热度、舆情、讨论度等非财务类软信息，可表现为指数、分值或聚合结果
- `SourceTrace`：来源追踪信息，用于记录数据来自哪个数据源、何时抓取、原始接口或原始文件是什么、经过了哪些处理步骤
- `QualityProfile`：质量画像，用于描述一条数据或一类数据的可信度、完整度、新鲜度、一致性、异常状态与适用性

上述 9 个核心对象在当前阶段应进一步收敛为如下“字段级定义草案”：

### 2.1 `Instrument` 字段草案

- `instrument_id`：系统内统一标的 ID
- `symbol`：统一代码
- `name`：标准名称
- `aliases`：别名 / 简称列表
- `instrument_type`：标的类型，如股票、指数、基金、行业、宏观指标
- `market`：市场，如 CN / HK / US
- `exchange`：交易所
- `currency`：计价币种
- `status`：上市 / 退市 / 停牌 / 有效等状态
- `source_mappings`：不同数据源下的代码映射关系

### 2.2 `Dataset` 字段草案

- `dataset_id`：数据集唯一标识
- `dataset_key`：稳定的数据集名称，如 `price.ohlcv.daily`
- `name`：数据集中文名称
- `domain`：所属数据域，如 price / fundamentals / documents / macro / sentiment
- `granularity`：粒度，如 tick / minute / day / report_period / page / event
- `description`：数据集说明
- `primary_keys`：主键字段定义
- `schema_version`：Schema 版本
- `default_source_priority`：默认数据源优先级
- `record_model`：对应的记录对象类型

### 2.3 `Record` 字段草案

- `record_id`：记录唯一标识
- `dataset_id`：所属数据集 ID
- `instrument_id`：所属标的 ID，可为空以支持宏观或无标的数据
- `observation_time`：观测时间 / 数据点时间
- `effective_time`：生效时间
- `published_time`：发布时间
- `values`：标准化业务字段集合
- `raw_values`：原始字段集合
- `trace_id`：来源追踪 ID
- `quality_id`：质量画像 ID

### 2.4 `Document` 字段草案

- `document_id`：文档唯一标识
- `instrument_id`：关联标的 ID
- `document_type`：文档类型，如年报、季报、公告、政策文件、研报
- `title`：文档标题
- `published_time`：发布时间
- `source_url`：原始链接
- `file_type`：文件类型，如 pdf / html / docx
- `file_hash`：文件哈希，用于去重与溯源
- `language`：文档语言
- `metadata`：文档补充元数据，如公告编号、报告期、作者等

### 2.5 `Citation` 字段草案

- `citation_id`：引用唯一标识
- `document_id`：所属文档 ID
- `page`：页码
- `section`：章节 / 标题
- `span`：文本区间或字符范围
- `quoted_text`：引用文本
- `locator`：定位信息，如页码 + 段落 + 坐标
- `source_url`：原始链接
- `file_hash`：引用对应文件哈希
- `confidence`：解析定位置信度

### 2.6 `Event` 字段草案

- `event_id`：事件唯一标识
- `event_type`：事件类型，如财报披露、宏观发布、停复牌、政策发布
- `title`：事件标题
- `instrument_id`：关联标的，可为空
- `market`：所属市场
- `scheduled_time`：计划发生时间
- `actual_time`：实际发生时间
- `published_time`：对外发布时间
- `payload`：事件业务数据内容
- `importance`：事件重要程度

### 2.7 `Sentiment` 字段草案

- `sentiment_id`：情绪记录唯一标识
- `instrument_id`：关联标的或主题 ID
- `topic`：主题 / 关键词
- `source`：情绪来源，如微信指数、雪球等
- `observation_time`：情绪观测时间
- `sentiment_type`：情绪类型，如热度、正负向、讨论度
- `score`：情绪分值
- `volume`：讨论量 / 样本量
- `method`：计算或聚合方法说明
- `raw_payload`：原始情绪数据内容

### 2.8 `SourceTrace` 字段草案

- `trace_id`：追踪唯一标识
- `source_name`：数据源名称
- `source_type`：来源类型，如 API / SDK / FILE / SCRAPER
- `source_endpoint`：原始接口或原始文件位置
- `fetched_at`：抓取时间
- `request_params`：请求参数摘要
- `cache_hit`：是否命中缓存
- `fallback_chain`：是否发生切源及切源链路
- `transform_steps`：标准化 / 解析处理步骤
- `raw_reference`：原始返回引用，如文件路径、响应 ID、快照 ID

### 2.9 `QualityProfile` 字段草案

- `quality_id`：质量画像唯一标识
- `completeness`：完整度
- `freshness`：新鲜度
- `consistency`：一致性
- `credibility`：可信度
- `latency`：时效延迟
- `anomaly_flags`：异常标记列表
- `warnings`：告警信息列表
- `applicability`：适用场景说明
- `evaluated_at`：质量评估时间

## Goal 3：定义统一接口与通用基类

基于 Goal 2 的资产模型，设计通用的数据引擎接口层与抽象基类，至少包括：

- 通用请求对象与领域子请求对象
- 通用响应对象（`records/meta/trace/quality/errors`）
- `BaseProvider`
- `BaseNormalizer`
- `BaseDocumentParser`
- `BaseResolver`
- 缓存、限频、重试、切源、溯源等运行时能力抽象

其中，通用响应对象中的各字段当前定义如下：

- `records`：正式业务数据内容，表示本次请求实际返回的数据主体；其内容应尽量是统一后的结构化记录列表，可对应行情记录、财报记录、公告页内容、宏观指标点、情绪信号等
- `meta`：响应元数据，表示“这次返回结果本身”的说明信息；通常包括数据集类型、请求参数、市场、时间范围、返回条数、分页信息、生成时间、返回格式版本等
- `trace`：来源与处理链路信息，表示“这些数据是怎么来的”；通常包括数据源名称、原始接口或原始文件、抓取时间、缓存命中情况、标准化步骤、切源情况、原始文档定位信息等
- `quality`：质量与可信度信息，表示“这些数据现在能不能放心用、适合怎么用”；通常包括完整度、可信度、新鲜度、一致性、异常标记、缺失说明、适用场景提示等
- `errors`：错误与告警信息，表示“这次请求过程中出现了哪些问题”；既包括致命错误，也包括非致命告警，例如部分字段缺失、部分来源失败、回退到备源、文档解析不完整、情绪数据覆盖不足等

标准响应建议采用如下 `JSON` 样例结构：

```json
{
  "records": [
    {
      "record_id": "rec_cn_600519_2024-12-31",
      "dataset_id": "ds_price_ohlcv_daily_v1",
      "instrument_id": "inst_cn_600519",
      "observation_time": "2024-12-31T00:00:00+08:00",
      "effective_time": "2024-12-31T15:00:00+08:00",
      "published_time": "2024-12-31T15:05:00+08:00",
      "values": {
        "open": 1688.0,
        "high": 1702.5,
        "low": 1679.2,
        "close": 1696.8,
        "volume": 321456,
        "amount": 545678900.0,
        "pct_change": 0.82
      },
      "raw_values": {
        "开盘": 1688.0,
        "最高": 1702.5,
        "最低": 1679.2,
        "收盘": 1696.8,
        "成交量": 321456,
        "成交额": 545678900.0,
        "涨跌幅": 0.82
      },
      "instrument": {
        "instrument_id": "inst_cn_600519",
        "symbol": "600519",
        "name": "贵州茅台",
        "aliases": ["茅台"],
        "instrument_type": "stock",
        "market": "CN",
        "exchange": "SSE",
        "currency": "CNY",
        "status": "active",
        "source_mappings": {
          "akshare": "600519",
          "eastmoney": "600519"
        }
      },
      "dataset": {
        "dataset_id": "ds_price_ohlcv_daily_v1",
        "dataset_key": "price.ohlcv.daily",
        "name": "股票日线行情",
        "domain": "price",
        "granularity": "day",
        "description": "股票日线 OHLCV 行情数据集",
        "primary_keys": ["instrument_id", "observation_time"],
        "schema_version": "v1",
        "default_source_priority": ["akshare", "tushare", "baostock"],
        "record_model": "Record"
      },
      "trace_id": "trace_20241231_001",
      "quality_id": "quality_20241231_001"
    }
  ],
  "meta": {
    "dataset_key": "price.ohlcv.daily",
    "request_id": "req_20260502_0001",
    "request_params": {
      "symbol": "600519",
      "market": "CN",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31"
    },
    "market": "CN",
    "time_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    },
    "record_count": 1,
    "page": 1,
    "page_size": 1,
    "response_schema_version": "v1",
    "generated_at": "2026-05-02T12:00:00+08:00"
  },
  "trace": {
    "trace_id": "trace_20241231_001",
    "source_name": "akshare",
    "source_type": "API",
    "source_endpoint": "stock_zh_a_hist",
    "fetched_at": "2026-05-02T11:59:58+08:00",
    "request_params": {
      "symbol": "600519",
      "adjust": "qfq"
    },
    "cache_hit": false,
    "fallback_chain": [],
    "transform_steps": [
      "provider.fetch",
      "normalizer.normalize",
      "quality.evaluate"
    ],
    "raw_reference": {
      "response_id": "ak_abcdef123456"
    }
  },
  "quality": {
    "quality_id": "quality_20241231_001",
    "completeness": 1.0,
    "freshness": 0.95,
    "consistency": 0.98,
    "credibility": 0.9,
    "latency": "PT5M",
    "anomaly_flags": [],
    "warnings": [],
    "applicability": ["research", "backtest"],
    "evaluated_at": "2026-05-02T12:00:00+08:00"
  },
  "errors": []
}
```

对于不同数据域，建议在同一响应外壳下派生不同的 `records` 载荷形态。以下给出补充样例：

### 文档 / 公告类标准响应样例

```json
{
  "records": [
    {
      "record_id": "rec_doc_600519_annual_report_page_3",
      "dataset_id": "ds_documents_announcements_pdf_parsed_v1",
      "instrument_id": "inst_cn_600519",
      "observation_time": "2024-04-03T19:30:00+08:00",
      "effective_time": "2024-04-03T19:30:00+08:00",
      "published_time": "2024-04-03T19:30:00+08:00",
      "values": {
        "page": 3,
        "text": "公司 2023 年实现营业总收入 ...",
        "char_count": 1268
      },
      "raw_values": {
        "pdf_page_index": 3,
        "raw_text": "公司2023年实现营业总收入..."
      },
      "document": {
        "document_id": "doc_cn_600519_2023_annual_report",
        "instrument_id": "inst_cn_600519",
        "document_type": "annual_report",
        "title": "贵州茅台 2023 年年度报告",
        "published_time": "2024-04-03T19:30:00+08:00",
        "source_url": "https://static.cninfo.com.cn/finalpage/.../P020240403.pdf",
        "file_type": "pdf",
        "file_hash": "sha256:abcdef123456",
        "language": "zh-CN",
        "metadata": {
          "announcement_id": "1234567890",
          "report_period": "2023-12-31"
        }
      },
      "citation": {
        "citation_id": "cite_doc_600519_page_3",
        "document_id": "doc_cn_600519_2023_annual_report",
        "page": 3,
        "section": "经营情况讨论与分析",
        "span": {"start": 120, "end": 246},
        "quoted_text": "公司 2023 年实现营业总收入 ...",
        "locator": "page=3;section=经营情况讨论与分析;span=120-246",
        "source_url": "https://static.cninfo.com.cn/finalpage/.../P020240403.pdf",
        "file_hash": "sha256:abcdef123456",
        "confidence": 0.97
      },
      "trace_id": "trace_doc_20240403_001",
      "quality_id": "quality_doc_20240403_001"
    }
  ],
  "meta": {
    "dataset_key": "documents.announcements.pdf.parsed",
    "request_id": "req_doc_20260502_0001",
    "request_params": {
      "symbol": "600519",
      "market": "CN",
      "keyword": "年度报告"
    },
    "market": "CN",
    "time_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    },
    "record_count": 1,
    "response_schema_version": "v1",
    "generated_at": "2026-05-02T12:10:00+08:00"
  },
  "trace": {
    "trace_id": "trace_doc_20240403_001",
    "source_name": "cninfo",
    "source_type": "FILE",
    "source_endpoint": "announcement_pdf",
    "fetched_at": "2026-05-02T12:09:58+08:00",
    "request_params": {"announcement_id": "1234567890"},
    "cache_hit": true,
    "fallback_chain": [],
    "transform_steps": [
      "provider.fetch",
      "document_parser.parse",
      "document_parser.extract_citations"
    ],
    "raw_reference": {
      "file_path": "cache/documents/cninfo/600519_2023_annual_report.pdf"
    }
  },
  "quality": {
    "quality_id": "quality_doc_20240403_001",
    "completeness": 0.98,
    "freshness": 0.88,
    "consistency": 0.96,
    "credibility": 0.95,
    "latency": "P394D",
    "anomaly_flags": [],
    "warnings": [],
    "applicability": ["research", "citation", "fundamental_analysis"],
    "evaluated_at": "2026-05-02T12:10:00+08:00"
  },
  "errors": []
}
```

### 财报 / 宏观 / 情绪类标准响应样例

```json
{
  "records": [
    {
      "record_id": "rec_fin_600519_2023-12-31",
      "dataset_id": "ds_fundamentals_financial_statements_normalized_v1",
      "instrument_id": "inst_cn_600519",
      "observation_time": "2023-12-31T00:00:00+08:00",
      "effective_time": "2024-04-03T19:30:00+08:00",
      "published_time": "2024-04-03T19:30:00+08:00",
      "values": {
        "revenue": 150560000000.0,
        "net_profit": 74734000000.0,
        "operating_cf": 92345000000.0,
        "inventory": 4890000000.0
      },
      "raw_values": {
        "TOTAL_OPERATE_INCOME": 150560000000.0,
        "PARENT_NETPROFIT": 74734000000.0,
        "NETCASH_OPERATE": 92345000000.0,
        "INVENTORY": 4890000000.0
      },
      "trace_id": "trace_fin_20240403_001",
      "quality_id": "quality_fin_20240403_001"
    },
    {
      "record_id": "rec_macro_cn_pmi_2024-12",
      "dataset_id": "ds_macro_pmi_monthly_v1",
      "instrument_id": null,
      "observation_time": "2024-12-01T00:00:00+08:00",
      "effective_time": "2024-12-31T09:30:00+08:00",
      "published_time": "2024-12-31T09:30:00+08:00",
      "values": {
        "indicator_code": "PMI_MANUFACTURING",
        "value": 50.3,
        "unit": "index_point",
        "region": "CN"
      },
      "raw_values": {
        "指标名称": "制造业采购经理指数",
        "本月": 50.3
      },
      "trace_id": "trace_macro_20241231_001",
      "quality_id": "quality_macro_20241231_001"
    },
    {
      "record_id": "rec_sentiment_wechat_ai_2025-01-03",
      "dataset_id": "ds_sentiment_wechat_index_daily_v1",
      "instrument_id": null,
      "observation_time": "2025-01-03T00:00:00+08:00",
      "effective_time": "2025-01-03T23:59:59+08:00",
      "published_time": "2025-01-04T00:10:00+08:00",
      "values": {
        "topic": "人工智能",
        "sentiment_type": "heat_index",
        "score": 842153,
        "volume": null,
        "method": "source_native_index"
      },
      "raw_values": {
        "keyword": "人工智能",
        "wechat_index": 842153
      },
      "sentiment": {
        "sentiment_id": "sent_wechat_ai_2025-01-03",
        "instrument_id": null,
        "topic": "人工智能",
        "source": "wechat_index",
        "observation_time": "2025-01-03T00:00:00+08:00",
        "sentiment_type": "heat_index",
        "score": 842153,
        "volume": null,
        "method": "source_native_index",
        "raw_payload": {
          "keyword": "人工智能",
          "index": 842153
        }
      },
      "trace_id": "trace_sentiment_20250104_001",
      "quality_id": "quality_sentiment_20250104_001"
    }
  ],
  "meta": {
    "dataset_key": "mixed.example",
    "request_id": "req_multi_20260502_0001",
    "request_params": {
      "domains": ["fundamentals", "macro", "sentiment"]
    },
    "market": "MULTI",
    "time_range": {
      "start": "2023-01-01",
      "end": "2025-01-03"
    },
    "record_count": 3,
    "response_schema_version": "v1",
    "generated_at": "2026-05-02T12:20:00+08:00"
  },
  "trace": {
    "trace_id": "trace_multi_20260502_0001",
    "source_name": "multi_source",
    "source_type": "MIXED",
    "source_endpoint": "aggregated_pipeline",
    "fetched_at": "2026-05-02T12:19:55+08:00",
    "request_params": {
      "include": ["eastmoney", "stats_gov", "wechat_index"]
    },
    "cache_hit": false,
    "fallback_chain": ["stats_gov -> wind_placeholder"],
    "transform_steps": [
      "provider.fetch",
      "normalizer.normalize",
      "resolver.resolve_source_mapping",
      "quality.evaluate"
    ],
    "raw_reference": {
      "batch_id": "batch_20260502_1220"
    }
  },
  "quality": {
    "quality_id": "quality_multi_20260502_0001",
    "completeness": 0.93,
    "freshness": 0.87,
    "consistency": 0.91,
    "credibility": 0.89,
    "latency": "PT10M",
    "anomaly_flags": ["sentiment_volume_missing"],
    "warnings": ["macro_source_fallback_applied"],
    "applicability": ["research", "signal_generation"],
    "evaluated_at": "2026-05-02T12:20:00+08:00"
  },
  "errors": [
    {
      "level": "warning",
      "code": "PARTIAL_SOURCE_FALLBACK",
      "message": "国家统计局主源暂不可用，宏观部分切换到预留链路。"
    }
  ]
}
```

补充约束说明：

- `records` 是主数据载体，可按不同数据域复用同一响应外壳，但内部 `values` / `raw_values` / 附属对象会随数据集变化
- 文档类数据建议在 `Record` 内显式挂接 `document` 与 `citation` 对象，便于引用与追溯
- 财报类数据建议优先保留 `values + raw_values` 双层结构，确保统一口径与源字段可同时访问
- 宏观与情绪类数据允许 `instrument_id` 为空，但仍需通过 `dataset`、`topic`、`indicator_code` 等字段保持可识别性
- `meta` 强调“本次响应”的边界信息，不重复承载单条记录级内容
- `trace` 强调来源与处理过程，后续可扩展为单条记录 trace 或批量 trace
- `quality` 默认可支持“整体结果级”质量画像，必要时也可以下沉到单条 `Record`
- `errors` 默认使用列表，保证即使主流程成功也能承载非致命告警

上述抽象基类在当前项目中的职责定义如下：

- `BaseProvider`：数据提供器基类，负责直接与具体外部数据源打交道，把原始接口、网页、文件或 SDK 数据取回；它关注“怎么从某个来源拿到数据”，但不负责统一业务口径
- `BaseNormalizer`：标准化器基类，负责把不同来源返回的原始字段、原始结构、原始口径转换为统一资产模型可接受的标准结构；它关注“怎么把不同源的数据变成统一语义”
- `BaseDocumentParser`：文档解析器基类，负责把 PDF、公告、研报、政策文件等文档类原始内容解析成结构化结果；它关注“怎么把文档变成可引用、可检索、可追溯的数据资产”
- `BaseResolver`：解析与映射器基类，负责把用户输入或外部标识解析成系统内部统一标识；它关注“怎么把名称、代码、别名、市场标识、数据源标识解析并映射到统一对象上”

进一步约束如下：

- `BaseProvider` 解决“取数”问题，不解决统一口径问题
- `BaseNormalizer` 解决“字段与语义统一”问题，不负责外部请求
- `BaseDocumentParser` 解决“文档内容结构化与引用”问题，不负责行情或财报标准化
- `BaseResolver` 解决“标识解析与对象映射”问题，是请求入口与底层数据源之间的重要桥梁

上述 4 个抽象基类在当前阶段应进一步补充“最小职责接口草案”：

### 3.1 `BaseProvider` 最小职责接口草案

- `provider_id()`：返回 Provider 唯一标识
- `capabilities()`：声明支持的数据集、市场、粒度与能力范围
- `validate_request(request)`：校验请求参数是否合法
- `fetch(request)`：向外部来源拉取原始数据
- `healthcheck()`：检查当前数据源可用性

最小职责边界：
- 输入：统一请求对象
- 输出：原始数据载荷 + 基础来源信息
- 不负责：统一标准字段定义、文档深度解析、标的解析总策略

### 3.2 `BaseNormalizer` 最小职责接口草案

- `supports(dataset_key)`：声明支持哪些数据集标准化
- `normalize(raw_payload, context)`：把原始载荷转成统一记录结构
- `validate_normalized(records)`：校验标准化后的结构完整性
- `schema_version()`：返回当前标准化所遵循的 schema 版本

最小职责边界：
- 输入：原始载荷 + 上下文信息
- 输出：标准化 `records`
- 不负责：直接请求外部源、缓存管理、重试与切源决策

### 3.3 `BaseDocumentParser` 最小职责接口草案

- `supports(file_type)`：声明支持哪些文档类型
- `parse(document, context)`：把原始文档解析成结构化内容
- `extract_citations(parsed_document)`：提取页级 / 段级引用对象
- `extract_metadata(document)`：提取文档级元数据

最小职责边界：
- 输入：文档文件、文档二进制或文档引用
- 输出：结构化文档内容 + `Citation` 列表
- 不负责：行情字段标准化、标的代码解析、源端下载调度策略

### 3.4 `BaseResolver` 最小职责接口草案

- `resolve_symbol(input_value, context)`：把名称 / 代码 / 别名解析成统一标的
- `resolve_market(input_value)`：解析市场标识
- `resolve_source_mapping(instrument, source_name)`：获取某个数据源下的映射代码
- `disambiguate(candidates, context)`：处理歧义候选

最小职责边界：
- 输入：用户输入、外部标识或候选对象
- 输出：统一 `Instrument` 或映射结果
- 不负责：拉取业务数据、执行标准化、解析文档正文

要求：

1. **所有正式接口优先返回结构化 `JSON`**，方便 Agent 与程序直接解析；
2. 新数据源接入必须有标准化流程，不允许每个 Provider 各写一套风格；
3. 必须能明确区分“源字段 raw 保留层”和“统一标准字段 normalized 层”；
4. 必须为后续商业源真实接入预留统一能力描述与接口占位。

## Goal 4：按新方案接入首批数据源

在新的 `data_engines/` 架构下，按统一标准接入首批真实数据源，并提供对应的样例与测试。

当前建议优先顺序：

1. `AkShare`：量价 / 基础行情
2. `东方财富`：财报 / 基本面聚合
3. `巨潮 / CNInfo`：公告 PDF / 文档元数据
4. `Tushare`、`BaoStock`：作为补充源与对照源
5. 交易所官方接口：作为官方口径与公告披露对照源
6. 商业源：只做能力接口预留，不做真实接入

要求：

1. 新实现必须位于 `data_engines/` 下；
2. 不以 `data_providers/` 目录结构为约束；
3. 适配过程中要同步产出映射关系、样例调用与边界说明；
4. 所有适配必须服从统一契约，而不是为单一 Provider 特判设计。

## Goal 5：建立测试、验收与稳定性治理能力

需要同时设计并逐步落地以下能力：

1. `schema` 层测试
2. `provider contract test`
3. `normalizer` 纯函数测试
4. `document parser` 测试
5. `resolver/symbol` 测试
6. 缓存 / 限频 / 重试 / 降级测试
7. 端到端样例与验收用例

并进一步保证：

- 数据真实性：来源清晰、可追溯、可引用
- 数据健壮性：接口稳定、失败可降级、异常可分类
- 数据实时性：合理的更新策略、缓存策略与滞后控制
- 数据可维护性：新数据源能低成本接入，旧数据源变更能局部收敛

---

# 交付要求

## 1. 文档交付

至少需要持续维护以下几类文档：

1. 数据源调研报告
2. 统一资产模型说明
3. 字段映射与数据集定义文档
4. 基类 / 接口 / 接入规范文档
5. 测试与验收标准文档
6. 阶段进展记录文档

## 2. 代码交付

至少需要包含以下类型的实现：

1. 统一 Schema / 模型定义
2. 统一接口层与抽象基类
3. 首批 Provider 适配实现
4. 统一运行时能力实现（缓存 / 限频 / 重试 / 溯源 / 切源）
5. 对应测试与样例

## 3. 返回格式要求

1. 面向 Agent 的主返回格式以结构化 `JSON` 为准；
2. 如确有必要，可在内部或调试阶段保留 `DataFrame`，但不应让其成为核心设计中心；
3. 必须为文档、公告、事件、情绪等非表格型数据提供清晰的统一表达方式；
4. 必须支持 `source trace`、质量标记和引用信息。

---

# 工作要求

1. 所有工作目录与产出结果放在 `data_engines/` 目录下面；
2. 如果有不明确的地方，需要首先跟我沟通确认；
3. 但凡已经明确的决策，不要反复回退到旧方案讨论；
4. 方案设计要以“更清晰的数据引擎架构”为第一优先级，而不是优先兼容旧代码；
5. 优先编辑和补充已有文档，除非新增文件确有必要；
6. 所有阶段都要记录“已完成 / 进行中 / 未开始”的进展。

---

# 工作流程

1. 先将核心目标拆解成更具体、可执行、可验收的阶段计划，并维护进展文档；
2. 先完成数据源调研框架与候选源矩阵，再进入统一资产模型设计；
3. 在统一资产模型明确之前，不要仓促开始大规模 Provider 编码；
4. 在统一接口与基类明确之后，再开始首批 Provider 适配；
5. 在适配过程中同步补测试、样例、字段映射和边界说明；
6. 每完成一个阶段，都要把结论回写到计划文档，确保后续工作有明确上下文；
7. 对于商业数据源，当前阶段完成能力分析、接口预留和占位设计即可，不要求真实打通。

---

# 当前阶段优先级

当前优先顺序如下：

1. 完成 Phase 1 数据源调研与能力矩阵
2. 完成 Phase 2 `JSON-first` 统一资产模型草案
3. 完成 Phase 3 统一接口与抽象基类草案
4. 再在 `data_engines/` 下独立落地首批数据引擎骨架与 Provider 适配

以上优先级已经明确，后续工作请围绕这个顺序推进。
