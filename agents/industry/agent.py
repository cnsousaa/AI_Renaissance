"""
行业景气 Agent - 专家5组

signal_type: industry
Skill 域: skills/industry/
核心能力：产业链景气度、行业拐点、竞争格局

数据获取原则（与项目规则对齐）：
- 真实 fetching / parsing / provider 逻辑放在 data_sources/ 层
- Agent 只调用 data_sources 接口，不直接联网抓数
- 当前使用 data_sources.industrial_sentinel.IndustrialSentinelDataSource
  （封装 IndustrySentiment + EastMoney，带缓存降级）
"""

from typing import Optional
from agents.base import BaseAgent
from agents.signal import Signal, neutral_signal

try:
    from skills.industry.industrial_sentinel.runtime import run_industrial_sentinel
except Exception:
    run_industrial_sentinel = None

# 项目共用复合数据源（data_sources/ 层封装，带缓存降级）
try:
    from data_sources.industrial_sentinel import IndustrialSentinelDataSource
except Exception:
    IndustrialSentinelDataSource = None


class IndustryAgent(BaseAgent):
    """行业景气 Agent（专家5组）"""

    signal_type = "industry"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(name="行业景气Agent", config=config or {})
        self.load_skills_from_domain("industry")
        # 复用数据源实例，避免每次 analyze 都新建
        self._data_source = None
        if IndustrialSentinelDataSource is not None:
            try:
                self._data_source = IndustrialSentinelDataSource()
            except Exception as e:
                self.log(f"数据源初始化失败：{e}", level="warning")

    def analyze(self, stock_code: str) -> Signal:
        """运行 industrial_sentinel skill，返回行业景气度 Signal。

        1. 从 data_sources.industrial_sentinel 获取原始数据（行业情绪 + 财务）
        2. 将原始 dict 传给 runtime.run_industrial_sentinel() 进行分析
        3. 将返回的 dict 通过 Signal.from_dict() 包装为标准 Signal
        4. Signal.from_dict 异常时返回 neutral_signal 并标记 needs_human_review
        """
        self.log(f"开始行业景气分析：{stock_code}")

        if run_industrial_sentinel is None:
            return neutral_signal(
                confidence=0.1,
                reasoning="industrial_sentinel runtime 导入失败",
                source=self.name,
                stock_code=stock_code,
                signal_type=self.signal_type,
                meta={"needs_human_review": True, "error": "runtime import failed"},
            )

        # ── Step 1: 从 data_sources 层获取数据（封装了缓存降级） ──
        industry_result = None
        financial_data = None
        degradation_reasons = []
        data_source_meta = {}

        ds = self._data_source
        if ds is not None:
            try:
                data = ds.get_data(stock_code)
                industry_result = data.get("industry_result")
                financial_data = data.get("financial_data")
                degradation_reasons = data.get("degradation_reasons", [])
                data_source_meta = {
                    "industry_from_cache": data.get("industry_from_cache", False),
                    "financial_from_cache": data.get("financial_from_cache", False),
                    "degradation_reasons": degradation_reasons,
                }
                if industry_result:
                    self.log("行业情绪数据获取成功")
                else:
                    self.log("行业情绪数据不可用", level="warning")
                if financial_data:
                    self.log("财务数据获取成功")
                else:
                    self.log("财务数据不可用", level="warning")
            except Exception as exc:
                self.log(f"IndustrialSentinelDataSource 获取失败：{exc}", level="error")
        else:
            self.log("IndustrialSentinelDataSource 不可用", level="warning")

        # ── Step 2: 调用 runtime 进行分析（只传数据 dict，不接触网络/磁盘） ──
        # 把降级原因通过 config 透传给 runtime，让 runtime 在 reasoning 中展示
        config_with_hints = dict(self.config)
        if degradation_reasons:
            config_with_hints["_degradation_reasons"] = degradation_reasons
        try:
            result = run_industrial_sentinel(
                stock_code,
                industry_result=industry_result,
                financial_data=financial_data,
                config=config_with_hints,
            )
        except Exception as exc:
            self.log(f"industrial_sentinel 执行失败：{exc}", level="error")
            return neutral_signal(
                confidence=0.1,
                reasoning=f"industrial_sentinel 执行异常: {exc}",
                source=self.name,
                stock_code=stock_code,
                signal_type=self.signal_type,
                meta={"needs_human_review": True, "error": str(exc)},
            )

        # ── Step 3: 构造 Signal（异常时返回 neutral_signal + needs_human_review） ──
        # 防御性预处理：先浅拷贝避免修改 caller 的 dict，再确保关键字段有效
        result = dict(result)
        result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.25) or 0.25)))
        if result.get("direction") not in ("bullish", "bearish", "neutral"):
            result["direction"] = "neutral"

        try:
            signal = Signal.from_dict(result)
        except Exception as exc:
            self.log(f"Signal 构造异常：{exc}", level="error")
            return neutral_signal(
                confidence=0.1,
                reasoning=f"Signal 构造异常: {exc}",
                source=self.name,
                stock_code=stock_code,
                signal_type=self.signal_type,
                meta={"needs_human_review": True, "error": str(exc), "raw_result": result},
            )

        signal.source = self.name
        signal.signal_type = self.signal_type
        if not signal.stock_code or signal.stock_code == "unknown":
            signal.stock_code = stock_code

        # 把数据源元信息写入 meta，便于 Orchestrator 追踪
        signal.meta["data_source"] = data_source_meta

        return signal
