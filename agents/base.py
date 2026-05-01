"""
Agent基类 - 所有Agent的父类
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from loguru import logger


class BaseAgent(ABC):
    """
    所有Agent的基类

    子类需要实现:
    - name: Agent名称
    - analyze(): 核心分析逻辑
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        logger.info(f"[{self.name}] Agent initialized")

    @abstractmethod
    def analyze(self, *args, **kwargs):
        """
        核心分析逻辑（子类必须实现）

        Returns:
            Signal: 标准化的信号对象
        """
        pass

    def pre_analyze(self, *args, **kwargs) -> Dict[str, Any]:
        """
        前置处理（可选重写）
        数据获取、预处理等
        """
        return {}

    def post_analyze(self, signal, *args, **kwargs):
        """
        后置处理（可选重写）
        信号校验、日志记录等
        """
        return signal

    def run(self, *args, **kwargs):
        """
        Agent执行入口（模板方法模式）
        """
        # 1. 前置处理
        context = self.pre_analyze(*args, **kwargs)

        # 2. 核心分析
        signal = self.analyze(*args, **kwargs, **context)

        # 3. 后置处理
        signal = self.post_analyze(signal, *args, **kwargs)

        return signal

    def log(self, message: str, level: str = "info"):
        """统一的日志记录"""
        getattr(logger, level)(f"[{self.name}] {message}")


class DataAgent(BaseAgent):
    """
    数据获取Agent基类
    专注于从各种数据源获取数据
    """

    def analyze(self, *args, **kwargs):
        # 数据Agent的analyze默认返回原始数据
        raise NotImplementedError("DataAgent should override analyze()")
