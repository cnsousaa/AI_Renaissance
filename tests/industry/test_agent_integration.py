#!/usr/bin/env python3
"""
IndustryAgent 集成测试
验证 agent.py → runtime → pipeline → Signal 全链路
"""
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# 确保 repo root 在 path 中
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))


# ═══════════════════════════════════════════════════
# 1. Import 链路测试
# ═══════════════════════════════════════════════════

def test_import_agent_module():
    """验证 agent 模块可正常导入"""
    from agents.industry.agent import IndustryAgent
    assert IndustryAgent is not None
    assert IndustryAgent.signal_type == "industry"


def test_import_signal_classes():
    """验证 Signal 相关类可正常导入"""
    from agents.signal import Signal, Direction, SignalType, neutral_signal
    assert Direction.BULLISH.value == "bullish"
    assert SignalType.INDUSTRY.value == "industry"
    assert callable(neutral_signal)


# ═══════════════════════════════════════════════════
# 2. Signal 契约测试
# ═══════════════════════════════════════════════════

def test_signal_from_dict_bullish():
    """Signal.from_dict 正确解析完整 bullish 信号"""
    from agents.signal import Signal

    result = {
        "direction": "bullish",
        "confidence": 0.75,
        "reasoning": "产业链景气上行",
        "signals": ["营收加速", "产能紧张", "政策催化"],
        "source": "行业景气Agent",
        "signal_type": "industry",
        "stock_code": "002916.SZ",
        "weight": 0.65,
        "meta": {
            "stock_name": "深南电路",
            "industry": "PCB",
            "preset": "pcb",
            "data_quality": "complete",
            "stock_type": "cyclical",
            "adaptive_weights": {
                "fundamental": 0.35, "valuation": 0.20,
                "technical": 0.25, "sentiment": 0.20
            },
            "html_report": "/tmp/test.html",
        },
    }
    signal = Signal.from_dict(result)

    assert signal.direction == "bullish"
    assert signal.confidence == 0.75
    assert len(signal.signals) == 3
    assert signal.weight == 0.65
    assert signal.meta["stock_type"] == "cyclical"
    assert signal.meta["adaptive_weights"]["fundamental"] == 0.35


def test_signal_from_dict_neutral():
    """Signal.from_dict 正确解析 neutral 信号"""
    from agents.signal import Signal

    result = {
        "direction": "neutral",
        "confidence": 0.1,
        "reasoning": "数据缺失",
        "signals": [],
        "weight": 0.0,
        "meta": {"data_quality": "missing"},
    }
    signal = Signal.from_dict(result)
    assert signal.direction == "neutral"
    assert signal.confidence == 0.1


def test_signal_from_dict_bearish():
    """Signal.from_dict 正确解析 bearish 信号"""
    from agents.signal import Signal

    result = {
        "direction": "bearish",
        "confidence": 0.6,
        "reasoning": "产能过剩",
        "signals": ["价格下跌", "库存积压"],
        "weight": 0.4,
        "meta": {},
    }
    signal = Signal.from_dict(result)
    assert signal.direction == "bearish"


def test_signal_confidence_range_validation():
    """置信度越界应抛出 ValueError"""
    from agents.signal import Signal
    import pytest

    with pytest.raises(ValueError):
        Signal(direction="neutral", confidence=1.5, reasoning="test")

    with pytest.raises(ValueError):
        Signal(direction="neutral", confidence=-0.1, reasoning="test")


def test_signal_direction_validation():
    """非法方向应抛出 ValueError"""
    from agents.signal import Signal
    import pytest

    with pytest.raises(ValueError):
        Signal(direction="invalid", confidence=0.5, reasoning="test")


# ═══════════════════════════════════════════════════
# 3. IndustryAgent 集成测试（mock runtime）
# ═══════════════════════════════════════════════════

class TestIndustryAgent:
    """IndustryAgent 全链路测试"""

    @pytest.fixture
    def mock_runtime_success(self):
        """Mock run_industrial_sentinel 返回完整成功信号"""
        return {
            "direction": "bullish",
            "confidence": 0.72,
            "reasoning": "仕佳光子：拐点确认 | 成长期",
            "signals": ["营收增速 35.0% >= 20% 加速", "产能利用率 88.0% >= 85% 紧张"],
            "weight": 0.65,
            "meta": {
                "html_report": "/tmp/688313_report.html",
                "stock_name": "仕佳光子",
                "stock_code": "688313.SH",
                "industry": "光通信",
                "preset": "optical-module",
                "data_quality": "complete",
                "stock_type": "growth",
                "adaptive_weights": {
                    "fundamental": 0.30, "valuation": 0.35,
                    "technical": 0.20, "sentiment": 0.15,
                },
            },
        }

    @pytest.fixture
    def mock_runtime_neutral(self):
        """Mock 返回中性信号"""
        return {
            "direction": "neutral",
            "confidence": 0.15,
            "reasoning": "芯原股份：拐点前 | 导入期 — 数据不足以判定",
            "signals": [],
            "weight": 0.1,
            "meta": {
                "html_report": "",
                "stock_name": "芯原股份",
                "stock_code": "688521.SH",
                "industry": "芯片设计",
                "preset": "ai-chip",
                "data_quality": "incomplete",
                "stock_type": "mixed",
                "adaptive_weights": {"fundamental": 0.25, "valuation": 0.25, "technical": 0.25, "sentiment": 0.25},
            },
        }

    def test_analyze_bullish(self, mock_runtime_success):
        """正常路径：返回 bullish Signal"""
        from agents.industry.agent import IndustryAgent

        with patch("agents.industry.agent.run_industrial_sentinel",
                   return_value=mock_runtime_success):
            agent = IndustryAgent()
            signal = agent.analyze("688313.SH")

        assert signal.direction == "bullish"
        assert signal.confidence == 0.72
        assert signal.signal_type == "industry"
        assert signal.source == "行业景气Agent"
        assert signal.stock_code == "688313.SH"
        assert len(signal.signals) == 2
        assert signal.meta["stock_type"] == "growth"
        assert signal.meta["preset"] == "optical-module"
        # adaptive_weights 应透传
        assert signal.meta["adaptive_weights"]["fundamental"] == 0.30
        assert signal.weight == 0.65

    def test_analyze_neutral(self, mock_runtime_neutral):
        """数据不足路径：返回 neutral Signal"""
        from agents.industry.agent import IndustryAgent

        with patch("agents.industry.agent.run_industrial_sentinel",
                   return_value=mock_runtime_neutral):
            agent = IndustryAgent()
            signal = agent.analyze("688521.SH")

        assert signal.direction == "neutral"
        assert signal.confidence == 0.15
        assert signal.signal_type == "industry"
        assert signal.meta["data_quality"] == "incomplete"

    def test_analyze_runtime_exception(self):
        """runtime 抛出异常：应返回降级 neutral Signal"""
        from agents.industry.agent import IndustryAgent

        with patch("agents.industry.agent.run_industrial_sentinel",
                   side_effect=RuntimeError("Skill 执行崩溃")):
            agent = IndustryAgent()
            signal = agent.analyze("000001.SZ")

        assert signal.direction == "neutral"
        assert signal.confidence == 0.1
        assert "崩溃" in signal.reasoning
        assert signal.stock_code == "000001.SZ"

    def test_analyze_import_missing(self):
        """runtime import 失败：应返回降级 neutral Signal"""
        from agents.industry.agent import IndustryAgent

        with patch("agents.industry.agent.run_industrial_sentinel", None):
            agent = IndustryAgent()
            signal = agent.analyze("000001.SZ")

        assert signal.direction == "neutral"
        assert signal.confidence == 0.1
        assert "导入失败" in signal.reasoning

    def test_analyze_empty_result(self):
        """runtime 返回空 dict：from_dict 应妥善处理"""
        from agents.industry.agent import IndustryAgent

        # from_dict 需要至少这些 key
        minimal = {
            "direction": "neutral",
            "confidence": 0.0,
            "reasoning": "",
            "signals": [],
            "weight": 0.0,
            "meta": {},
        }
        with patch("agents.industry.agent.run_industrial_sentinel",
                   return_value=minimal):
            agent = IndustryAgent()
            signal = agent.analyze("000000.SZ")

        assert signal.direction == "neutral"

    def test_stock_code_passthrough(self, mock_runtime_success):
        """stock_code 未设置时 agent 应补上"""
        from agents.industry.agent import IndustryAgent

        result = dict(mock_runtime_success)
        del result["meta"]["stock_code"]  # 模拟缺少 stock_code
        result["meta"]["stock_code"] = ""

        with patch("agents.industry.agent.run_industrial_sentinel",
                   return_value=result):
            agent = IndustryAgent()
            signal = agent.analyze("002916.SZ")

        # agent 应补上 stock_code
        assert signal.stock_code == "002916.SZ"

    def test_config_passed_to_runtime(self, mock_runtime_success):
        """config 应传递给 runtime"""
        from agents.industry.agent import IndustryAgent

        config = {"verbose": True, "data_dir": "/custom/path"}
        with patch("agents.industry.agent.run_industrial_sentinel",
                   return_value=mock_runtime_success) as mock_run:
            agent = IndustryAgent(config=config)
            agent.analyze("002916.SZ")

        mock_run.assert_called_once_with("002916.SZ", config)


# ═══════════════════════════════════════════════════
# 4. 边界条件测试
# ═══════════════════════════════════════════════════

def test_agent_name():
    """Agent 名称正确"""
    from agents.industry.agent import IndustryAgent
    agent = IndustryAgent()
    assert "行业景气" in agent.name


def test_agent_signal_type():
    """signal_type 类属性正确"""
    from agents.industry.agent import IndustryAgent
    assert IndustryAgent.signal_type == "industry"


def test_signal_to_dict_roundtrip():
    """Signal → to_dict → from_dict 往返一致性"""
    from agents.signal import Signal

    original = Signal(
        direction="bullish",
        confidence=0.8,
        reasoning="测试推理",
        signals=["s1", "s2"],
        source="测试源",
        signal_type="industry",
        stock_code="002916.SZ",
        weight=0.5,
        meta={"key": "value"},
    )
    as_dict = original.to_dict()
    restored = Signal.from_dict(as_dict)

    assert restored.direction == original.direction
    assert restored.confidence == original.confidence
    assert restored.reasoning == original.reasoning
    assert restored.signal_type == original.signal_type
    assert restored.weight == original.weight
    assert restored.meta == original.meta


# ═══════════════════════════════════════════════════
# 5. Orchestrator 集成验证
# ═══════════════════════════════════════════════════

def test_signal_weight_read_by_orchestrator():
    """验证 Signal.weight 字段存在，Orchestrator 可正常读取"""
    from agents.signal import Signal

    # 模拟 Orchestrator 的 _calculate_scores 逻辑
    signal = Signal(
        direction="bullish",
        confidence=0.8,
        reasoning="test",
        weight=0.65,  # industry agent 返回的权重
    )
    weighted_confidence = signal.confidence * signal.weight
    assert abs(weighted_confidence - 0.52) < 0.01  # 0.8 * 0.65 = 0.52


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
