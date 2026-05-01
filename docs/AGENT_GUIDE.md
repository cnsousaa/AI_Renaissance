# Agent开发指南 - 5分钟上手

> 你只需要关心一件事：**实现 `analyze()` 方法**

---

## 一、目录结构

每个Agent都有自己的文件夹，按分类放置：

```
agents/
├── perception/          # 感知层（数据获取）
│   └── 你的Agent名/
│       ├── __init__.py
│       ├── config.py    # 配置文件
│       └── agent.py     # 核心逻辑（你写这里）
│
├── research/            # 研究层（信号生成）
│   └── 你的Agent名/
│       └── ...
│
└── risk/               # 风控层
    └── ...
```

---

## 二、最简Agent模板

**复制粘贴这个模板，改一改就能用！**

```python
# agents/research/你的分类/你的Agent名/agent.py

from agents.base import BaseAgent
from agents.signal import Signal, bullish_signal, bearish_signal, neutral_signal


class YourAgent(BaseAgent):
    """你的Agent描述"""

    def __init__(self, config: dict):
        super().__init__(name="你的Agent名", config=config)
        # 在这里定义你的参数
        self.my_param = config.get("my_param", 默认值)

    def analyze(self, stock_code: str) -> Signal:
        """
        核心分析逻辑（你写这里）

        Args:
            stock_code: 股票代码，如 "000001"

        Returns:
            Signal对象（标准化信号）
        """
        # ===== 1. 获取数据（示例） =====
        # data = get_data(stock_code)
        data = {"示例": "数据"}  # 实际这里获取真实数据

        # ===== 2. 你的分析逻辑 =====
        # 计算指标、判断方向...

        # 示例：简单判断
        score = 0.8  # 你的分析结果

        # ===== 3. 返回标准化信号 =====
        if score > 0.6:
            # 看多信号
            return bullish_signal(
                confidence=score,                              # 置信度 0~1
                reasoning="你的判断理由，例如：XXX指标显示向好",  # 为什么
                signals=["具体信号1", "具体信号2"],              # 检测到的信号
                source=self.name,                              # Agent名称
                stock_code=stock_code,                        # 股票代码
                signal_type="financial",                       # 信号类型
                meta={"score": score}                          # 额外数据
            )
        elif score < 0.4:
            # 看空信号
            return bearish_signal(
                confidence=1.0 - score,
                reasoning="你的判断理由",
                signals=["风险信号1", "风险信号2"],
                source=self.name,
                stock_code=stock_code,
                signal_type="financial",
            )
        else:
            # 中性信号
            return neutral_signal(
                confidence=0.5,
                reasoning="多空力量均衡，暂无明显信号",
                source=self.name,
                stock_code=stock_code,
            )

    def batch_analyze(self, stock_codes: list) -> list:
        """批量分析（可选实现）"""
        return [self.analyze(code) for code in stock_codes]
```

---

## 三、配置文件模板

```python
# agents/research/你的分类/你的Agent名/config.py

CONFIG = {
    # Agent基本信息
    "name": "你的Agent名",
    "version": "0.1",
    "author": "你的名字",

    # 分析参数
    "param1": 100,              # 参数1说明
    "param2": 0.05,             # 参数2说明

    # 置信度阈值
    "confidence_threshold": 0.6,  # 低于此值不输出信号

    # 股票范围（可选）
    "stocks": ["000001", "600519"],  # 分析哪些股票
}
```

---

## 四、__init__.py 模板

```python
# agents/research/你的分类/你的Agent名/__init__.py

from .agent import YourAgent

__all__ = ["YourAgent"]
```

---

## 五、Signal对象详解

你**必须**返回 `Signal` 对象，格式如下：

```python
from agents.signal import Signal

signal = Signal(
    direction="bullish",       # 必须："bullish" | "bearish" | "neutral"
    confidence=0.85,          # 必须：0.0 ~ 1.0（浮点数）
    reasoning="为什么看多",    # 必须：文字说明
    signals=["信号1", "信号2"],  # 可选：检测到的具体信号列表
    source="你的Agent名",      # 必须：Agent名称
    signal_type="financial",   # 可选：信号类型
    stock_code="000001",      # 可选：股票代码
    weight=1.0,              # 可选：权重（仲裁层用）
    meta={"key": "value"}      # 可选：额外数据
)
```

### 便捷函数（推荐用这个）

```python
from agents.signal import bullish_signal, bearish_signal, neutral_signal

# 看多信号
signal = bullish_signal(
    confidence=0.8,
    reasoning="...",
    signals=["...", "..."],
    source="你的Agent",
    stock_code="000001"
)

# 看空信号
signal = bearish_signal(...)

# 中性信号
signal = neutral_signal(...)
```

---

## 六、常见数据类型与计算

### 6.1 涨跌幅计算

```python
def calculate_change_pct(current, previous):
    """计算涨跌幅"""
    if previous == 0:
        return 0.0
    return (current - previous) / abs(previous)
```

### 6.2 同比增长率

```python
def calculate_yoy_growth(current, last_year):
    """计算同比增长率"""
    if last_year == 0:
        return 0.0
    return (current - last_year) / abs(last_year)
```

### 6.3 均线计算

```python
import pandas as pd

def calculate_ma(prices: list, window: int) -> float:
    """计算简单移动平均"""
    if len(prices) < window:
        return 0.0
    return sum(prices[-window:]) / window
```

---

## 七、如何测试你的Agent

### 方法1：直接运行

```python
# test_your_agent.py
from agents.research.你的分类.你的Agent名.agent import YourAgent
from agents.research.你的分类.你的Agent名.config import CONFIG

# 创建Agent
agent = YourAgent(CONFIG)

# 测试单只股票
signal = agent.analyze("000001")
print(signal)

# 测试批量
signals = agent.batch_analyze(["000001", "600519"])
for s in signals:
    print(s)
```

运行：
```bash
cd AIRenaissance
python test_your_agent.py
```

### 方法2：集成到主程序

修改 `main.py` 中的 `collect_signals()` 函数，添加你的Agent：

```python
# main.py 中找到 collect_signals() 函数

# 添加你的Agent
from agents.research.你的分类.你的Agent名.agent import YourAgent

agent = YourAgent(config={})
signal = agent.analyze(stock_code)
bundle.add(signal)
```

---

## 八、常见问题

### Q1: 我不会Python怎么办？

**A**: 先学基础（2小时），然后：
1. 复制模板
2. 改一改参数
3. 用AI帮你写分析逻辑
4. 问我！

### Q2: 数据从哪里来？

**A**: 项目会提供统一的数据接口，你可以：
- 调用 `perception/` 下的数据Agent
- 直接请求API（东方财富、腾讯自选股）
- 先用假数据测试逻辑

### Q3: 置信度怎么定？

**A**: 经验法则：
- 0.9+：非常确定（如合同负债+200%）
- 0.7~0.9：比较确定（如净利润增长30%）
- 0.5~0.7：有可能（如技术指标金叉）
- <0.5：不确定，建议返回 `neutral`

### Q4: 如何处理错误？

**A**: 用 `try...except` 包裹你的逻辑：

```python
def analyze(self, stock_code: str) -> Signal:
    try:
        # 你的逻辑
        return signal
    except Exception as e:
        # 出错时返回中性信号
        return neutral_signal(
            confidence=0.1,
            reasoning=f"分析出错：{str(e)}",
            source=self.name,
            stock_code=stock_code,
        )
```

### Q5: 如何调试？

**A**: 用 `self.log()` 打印日志：

```python
def analyze(self, stock_code: str) -> Signal:
    self.log(f"开始分析 {stock_code}")
    # ...
    self.log(f"计算结果：{result}")
    return signal
```

---

## 九、任务认领流程

1. **在群里说**：「我要做 [某类] Agent」
2. **创建Issue**：在GitHub上创建Issue，格式：
   ```markdown
   ## Agent名称
   [你的名字]的[某类]Agent

   ## 分析逻辑
   简要描述你的分析思路

   ## 预计完成
   Week X
   ```
3. **开发**：按本文档指引开发
4. **提交**：Fork → 开发 → PR
5. **集成**：我来把你的Agent加入主程序

---

## 十、完整示例：现金流验证Agent

```python
# agents/research/financial/cash_flow/agent.py

from agents.base import BaseAgent
from agents.signal import Signal, bullish_signal, bearish_signal


class CashFlowAgent(BaseAgent):
    """现金流验证Agent"""

    def __init__(self, config: dict):
        super().__init__(name="现金流验证Agent", config=config)

    def analyze(self, stock_code: str) -> Signal:
        # 1. 获取数据（示例）
        financial_data = self._get_data(stock_code)

        # 2. 计算现金流比率
        ratio = financial_data["cash_flow"] / financial_data["net_profit"]

        # 3. 判断
        if ratio > 1.2:
            return bullish_signal(
                confidence=min(ratio / 2.0, 0.95),
                reasoning=f"经营现金流/净利润 = {ratio:.2f}，利润质量优秀",
                signals=[f"现金流比率{ratio:.2f}"],
                source=self.name,
                stock_code=stock_code,
                signal_type="financial",
            )
        elif ratio < 0.8:
            return bearish_signal(
                confidence=min((1.0 - ratio) / 0.5, 0.9),
                reasoning=f"经营现金流/净利润 = {ratio:.2f}，利润质量存疑",
                signals=[f"现金流比率{ratio:.2f}"],
                source=self.name,
                stock_code=stock_code,
                signal_type="financial",
            )
        else:
            from agents.signal import neutral_signal
            return neutral_signal(
                confidence=0.5,
                reasoning=f"现金流比率{ratio:.2f}，处于合理区间",
                source=self.name,
                stock_code=stock_code,
                signal_type="financial",
            )

    def _get_data(self, stock_code: str) -> dict:
        """获取数据（待实现API对接）"""
        # TODO: 对接东方财富API
        return {
            "cash_flow": 150000000,  # 经营现金流
            "net_profit": 100000000,  # 净利润
        }
```

---

**最后**：有任何问题，在群里@我！
