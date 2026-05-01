"""
现金流验证Agent - 示例Agent

职责：
1. 获取财报数据
2. 验证经营现金流与净利润的关系
3. 输出标准化Signal
"""

from typing import Dict, Any, List
from agents.base import BaseAgent
from agents.signal import Signal, bullish_signal, bearish_signal, neutral_signal


class CashFlowAgent(BaseAgent):
    """
    现金流验证Agent

    逻辑：
    - 经营现金流净额 / 净利润 > 1.2 → 利润质量高（看多信号）
    - 经营现金流净额 / 净利润 < 0.8 → 利润质量存疑（看空信号）
    - 介于之间 → 中性
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(name="现金流验证Agent", config=config)
        self.confidence_threshold = config.get("confidence_threshold", 0.6)
        self.periods = config.get("periods", 4)  # 分析最近4个季度

    def analyze(self, stock_code: str, financial_data: Dict = None) -> Signal:
        """
        分析一只股票的现金流质量

        Args:
            stock_code: 股票代码，如 "000001"
            financial_data: 财报数据（可选，如不提供则自动获取）

        Returns:
            Signal: 标准化信号
        """
        self.log(f"开始分析 {stock_code}")

        # ===== Step 1: 获取数据（这里是示例，实际需要调用API） =====
        if not financial_data:
            financial_data = self._fetch_financial_data(stock_code)

        # ===== Step 2: 计算核心指标 =====
        cash_flow_ratio = self._calculate_cash_flow_ratio(financial_data)

        # ===== Step 3: 生成信号 =====
        if cash_flow_ratio > 1.2:
            # 现金质量高 → 看多
            return bullish_signal(
                confidence=min(cash_flow_ratio / 2.0, 0.95),  # 越高越可信
                reasoning=f"经营现金流/净利润 = {cash_flow_ratio:.2f}，利润质量优秀",
                signals=[
                    f"经营现金流净额/净利润 = {cash_flow_ratio:.2f}",
                    "利润含金量高，现金流健康"
                ],
                source=self.name,
                stock_code=stock_code,
                signal_type="financial",
                meta={"cash_flow_ratio": cash_flow_ratio}
            )

        elif cash_flow_ratio < 0.8:
            # 现金质量存疑 → 看空
            return bearish_signal(
                confidence=min((1.0 - cash_flow_ratio) / 0.5, 0.9),
                reasoning=f"经营现金流/净利润 = {cash_flow_ratio:.2f}，利润质量存疑",
                signals=[
                    f"经营现金流净额/净利润 = {cash_flow_ratio:.2f}",
                    "可能存在应收账款积压或存货周转问题"
                ],
                source=self.name,
                stock_code=stock_code,
                signal_type="financial",
                meta={"cash_flow_ratio": cash_flow_ratio}
            )

        else:
            # 中性
            return neutral_signal(
                confidence=0.5,
                reasoning=f"经营现金流/净利润 = {cash_flow_ratio:.2f}，处于合理区间",
                source=self.name,
                stock_code=stock_code,
                signal_type="financial",
                meta={"cash_flow_ratio": cash_flow_ratio}
            )

    def _fetch_financial_data(self, stock_code: str) -> Dict:
        """
        获取财报数据（示例）

        实际实现需要调用：
        - 东方财富API
        - 或腾讯自选股API
        """
        # TODO: 实际对接API
        self.log(f"获取 {stock_code} 的财报数据（待实现API对接）", level="warning")

        # 返回示例数据
        return {
            "net_profit": 100000000,      # 净利润 1亿
            "operate_cash_flow": 150000000,  # 经营现金流 1.5亿
        }

    def _calculate_cash_flow_ratio(self, financial_data: Dict) -> float:
        """计算现金流比率"""
        net_profit = financial_data.get("net_profit", 1)  # 防止除零
        cash_flow = financial_data.get("operate_cash_flow", 0)

        if net_profit == 0:
            return 0.0

        return cash_flow / abs(net_profit)

    def batch_analyze(self, stock_codes: List[str]) -> List[Signal]:
        """批量分析"""
        return [self.analyze(code) for code in stock_codes]
