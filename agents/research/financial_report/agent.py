"""
财务专家 Agent

调用 skills/financial_report_analysis/SKILL.md 中的七步验证链，
对指定股票进行深度财报分析，输出标准 Signal。

架构关系：
  Skill（魂）  ← skills/financial_report_analysis/SKILL.md
  Agent（壳）  ← 本文件（负责调用 Skill，封装 Signal）
"""

from pathlib import Path
from typing import Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from agents.base import BaseAgent
from agents.signal import Signal, bullish_signal, bearish_signal, neutral_signal


class FinancialReportAgent(BaseAgent):
    """
    财务专家 Agent

    触发逻辑：
      1. 加载 skills/financial_report_analysis/SKILL.md 作为分析框架
      2. 通过东方财富 API 拉取三张表数据
      3. 将数据和 Skill Prompt 一起发给 LLM 分析
      4. 解析 LLM 输出，封装成标准 Signal 返回
    """

    def __init__(self, config: Optional[dict] = None):
        super().__init__(name="财务专家Agent", config=config or {})
        self.skill_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "skills" / "financial_report_analysis" / "SKILL.md"
        )
        self.skill_content = ""
        self._load_skill()

    def _load_skill(self):
        """加载 Skill 文件内容"""
        try:
            self.skill_content = self.skill_path.read_text(encoding="utf-8")
            self.log(f"已加载 Skill：{self.skill_path}")
        except FileNotFoundError:
            self.log(f"Skill 文件不存在：{self.skill_path}", "error")
            self.skill_content = "# 财报分析\n请分析现金流、合同负债、资本开支等指标。"

    # ── 公开入口 ────────────────────────────────────────────────

    def analyze(self, stock_code: str) -> Signal:
        """
        分析指定股票的财报质量

        Args:
            stock_code: 股票代码，支持格式：600519、SZ300757、SH600519

        Returns:
            标准 Signal 对象
        """
        self.log(f"开始分析股票：{stock_code}")

        # 1. 标准化股票代码
        eastmoney_code = self._normalize_code(stock_code)
        if not eastmoney_code:
            return neutral_signal(
                confidence=0.1,
                reasoning=f"无法识别股票代码：{stock_code}",
                source=self.name,
                stock_code=stock_code,
            )

        # 2. 拉取财务数据
        financial_data = self._fetch_financial_data(eastmoney_code)
        if not financial_data:
            return neutral_signal(
                confidence=0.1,
                reasoning=f"无法获取股票 {stock_code} 的财务数据",
                source=self.name,
                stock_code=stock_code,
            )

        # 3. 调用 LLM 按 Skill 框架分析
        analysis_result = self._analyze_with_skill(financial_data, stock_code)
        if not analysis_result:
            return neutral_signal(
                confidence=0.3,
                reasoning="LLM 分析未返回有效结果，建议人工复核",
                source=self.name,
                stock_code=stock_code,
            )

        # 4. 解析结果，封装成 Signal
        return self._build_signal(analysis_result, stock_code)

    # ── 股票代码标准化 ────────────────────────────────────────

    def _normalize_code(self, code: str) -> str:
        """
        把用户输入的股票代码转成东方财富 API 需要的格式
        600519   → SZ600519?  → 实际沪市用 SH，深市用 SZ
        注意：东方财富 API 参数 code=SZ300757（需要带前缀）
        """
        code = code.strip().upper()
        if code.startswith("SH") or code.startswith("SZ"):
            return code
        if code.startswith("6"):
            return f"SH{code}"
        if code.startswith(("0", "3")):
            return f"SZ{code}"
        self.log(f"无法识别的股票代码格式：{code}", "warning")
        return ""

    # ── 获取财务数据 ─────────────────────────────────────────

    def _fetch_financial_data(self, eastmoney_code: str) -> dict:
        """
        通过东方财富 API 拉取三张表的最新一期数据

        API 文档见 Skill 文件中的"执行流程"章节
        """
        if not HAS_REQUESTS:
            self.log("requests 库未安装，无法获取财务数据", "error")
            return {}

        base_url = "https://emweb.eastmoney.com/NewFinanceAnalysis"
        # 动态获取最新报告期（季报披露截止日后，才能拿到该季报数据）
        # 报告期 vs 披露截止日：Q1(03-31)→4/30  Q2(06-30)→8/31  Q3(09-30)→10/31  Q4(12-31)→次年4/30
        from datetime import datetime
        today = datetime.now()
        report_date = None
        if today >= datetime(today.year + 1, 4, 30):
            # 次年4月30日之后 → 可拿今年Q4数据（12-31）
            report_date = f"{today.year}-12-31"
        elif today >= datetime(today.year, 10, 31):
            # 10月31日之后 → 可拿Q3数据（09-30）
            report_date = f"{today.year}-09-30"
        elif today >= datetime(today.year, 8, 31):
            # 8月31日之后 → 可拿Q2数据（06-30）
            report_date = f"{today.year}-06-30"
        elif today >= datetime(today.year, 4, 30):
            # 4月30日之后 → 可拿Q1数据（03-31）
            report_date = f"{today.year}-03-31"
        else:
            # 4月30日之前 → 只能拿去年Q4数据（去年12-31）
            report_date = f"{today.year - 1}-12-31"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://emweb.eastmoney.com/",
        }

        urls = {
            "balance":   f"{base_url}/zcfzbAjaxNew?companyType=4&reportDateType=0&reportType=1&dates={report_date}&code={eastmoney_code}",
            "income":     f"{base_url}/lrbAjaxNew?companyType=4&reportDateType=0&reportType=1&dates={report_date}&code={eastmoney_code}",
            "cashflow":   f"{base_url}/xjllbAjaxNew?companyType=4&reportDateType=0&reportType=1&dates={report_date}&code={eastmoney_code}",
        }

        results = {}
        for sheet_name, url in urls.items():
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                results[sheet_name] = resp.json()
                self.log(f"获取{sheet_name}数据成功：{eastmoney_code}")
            except Exception as e:
                self.log(f"获取{sheet_name}数据失败：{e}", "error")
                results[sheet_name] = {}

        return results

    # ── 调用 Skill 分析 ─────────────────────────────────────

    def _analyze_with_skill(self, financial_data: dict, stock_code: str) -> dict:
        """
        把 Skill Prompt + 财务数据一起发给 LLM，
        按 Skill 中的七步验证链进行分析。

        返回解析后的字典，包含 direction / confidence / reasoning / signals。
        """
        # 构造用户消息：把财务数据塞进去
        user_message = self._format_data_for_llm(financial_data, stock_code)

        # ── 方式 A：有 OpenAI API Key，直接调用 ──
        api_key = self.config.get("openai_api_key") or ""
        if api_key and HAS_REQUESTS:
            return self._call_openai(api_key, user_message)

        # ── 方式 B：无 API Key，用规则引擎本地计算（降级方案）──
        self.log("未配置 OpenAI API Key，使用本地规则引擎降级分析")
        return self._fallback_rule_engine(financial_data, stock_code)

    def _format_data_for_llm(self, financial_data: dict, stock_code: str) -> str:
        """把 API 返回的 JSON 数据格式化成 LLM 可读的文本"""
        parts = [f"股票代码：{stock_code}\n"]
        for sheet_name, data in financial_data.items():
            parts.append(f"## {sheet_name}\n{data}\n")
        return "\n".join(parts)

    def _call_openai(self, api_key: str, user_message: str) -> dict:
        """调用 OpenAI API 按 Skill 框架分析"""
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": self.config.get("model", "gpt-4o"),
                    "messages": [
                        {"role": "system", "content": self.skill_content},
                        {"role": "user",   "content": user_message},
                    ],
                    "response_format": {"type": "json_object"},
                },
                timeout=30,
            )
            resp.raise_for_status()
            import json
            return json.loads(resp.json()["choices"][0]["message"]["content"])
        except Exception as e:
            self.log(f"OpenAI API 调用失败：{e}", "error")
            return {}

    # ── 降级方案：本地规则引擎（完整七步验证链）──────────

    # 七步验证链定义（与 SKILL.md 保持一致）
    SEVEN_STEPS = [
        {
            "step": 1,
            "name": "看现金",
            "description": "利润是不是被现金撑住",
            "metrics": ["经营现金流/净利润", "销售收现/营收"],
            "icon": "💰",
        },
        {
            "step": 2,
            "name": "看需求",
            "description": "营运资本位置对不对",
            "metrics": ["应收账款变化", "收现能力变化"],
            "icon": "📦",
        },
        {
            "step": 3,
            "name": "看业绩",
            "description": "合同负债/预收款先行指标",
            "metrics": ["合同负债同比变化"],
            "icon": "📋",
        },
        {
            "step": 4,
            "name": "看产能",
            "description": "是否已在扩产",
            "metrics": ["在建工程", "固定资产", "资本开支"],
            "icon": "🏭",
        },
        {
            "step": 5,
            "name": "看扩张",
            "description": "资本开支力度",
            "metrics": ["购建固定资产支付的现金"],
            "icon": "📈",
        },
        {
            "step": 6,
            "name": "看扩张风险",
            "description": "净债务水平",
            "metrics": ["短期借款变化", "长期借款变化", "财务费用"],
            "icon": "⚠️",
        },
        {
            "step": 7,
            "name": "看利率敏感度",
            "description": "财务费用侵蚀",
            "metrics": ["财务费用/营业利润"],
            "icon": "🏦",
        },
    ]

    def _fallback_rule_engine(self, financial_data: dict, stock_code: str) -> dict:
        """
        本地规则引擎（不依赖 LLM）
        完整实现 Skill 七步验证链，对每个步骤逐一评分。
        """
        reasoning_steps = []  # 收集每一步的推理结果
        # bullish_score[0]=计数, [1]=权重; bearish_score 同理
        bullish_score = [0, 0]
        bearish_score = [0, 0]
        total_weight = [0]  # 用列表以便在函数内修改

        try:
            balance_data   = financial_data.get("balance",   {}).get("data", [{}])[0]
            income_data    = financial_data.get("income",   {}).get("data", [{}])[0]
            cashflow_data  = financial_data.get("cashflow",  {}).get("data", [{}])[0]

            # ── 第一步：看现金 ──────────────────────────────────
            step1 = self._step1_cash(income_data, cashflow_data)
            reasoning_steps.append(step1)
            self._score_step(step1, bullish_score, bearish_score, total_weight)

            # ── 第二步：看需求 ──────────────────────────────────
            step2 = self._step2_demand(balance_data, cashflow_data, income_data)
            reasoning_steps.append(step2)
            self._score_step(step2, bullish_score, bearish_score, total_weight)

            # ── 第三步：看业绩 ──────────────────────────────────
            step3 = self._step3_performance(balance_data)
            reasoning_steps.append(step3)
            self._score_step(step3, bullish_score, bearish_score, total_weight)

            # ── 第四步：看产能 ──────────────────────────────────
            step4 = self._step4_capacity(balance_data, cashflow_data)
            reasoning_steps.append(step4)
            self._score_step(step4, bullish_score, bearish_score, total_weight)

            # ── 第五步：看扩张 ──────────────────────────────────
            step5 = self._step5_expansion(cashflow_data)
            reasoning_steps.append(step5)
            self._score_step(step5, bullish_score, bearish_score, total_weight)

            # ── 第六步：看扩张风险 ──────────────────────────────────
            step6 = self._step6_risk(balance_data)
            reasoning_steps.append(step6)
            self._score_step(step6, bullish_score, bearish_score, total_weight)

            # ── 第七步：看利率敏感度 ──────────────────────────────────
            step7 = self._step7_interest(income_data)
            reasoning_steps.append(step7)
            self._score_step(step7, bullish_score, bearish_score, total_weight)

            # ── 综合判断 ──────────────────────────────────
            return self._build_verdict(
                bullish_score, bearish_score, total_weight,
                reasoning_steps, stock_code
            )

        except Exception as e:
            self.log(f"本地规则引擎出错：{e}", "error")
            import traceback
            self.log(traceback.format_exc(), "error")
            return {
                "direction": "neutral",
                "confidence": 0.2,
                "reasoning": f"本地分析出错：{str(e)}",
                "signals": [],
                "reasoning_steps": [],
            }

    def _score_step(self, step: dict, bullish_score, bearish_score, total_weight):
        """根据步骤评分，更新全局计数"""
        status = step.get("status", "neutral")
        weight = step.get("weight", 1)
        if status == "bullish":
            bullish_score[0] += weight
            bullish_score[1] += weight
        elif status == "bearish":
            bearish_score[0] += weight
            bearish_score[1] += weight
        total_weight[0] += weight

    def _build_verdict(self, bullish_score, bearish_score, total_weight,
                       reasoning_steps, stock_code) -> dict:
        """综合七步结果，给出最终判断"""
        b_cnt, b_weight = bullish_score
        r_cnt, r_weight = bearish_score
        total = total_weight[0]

        if total == 0:
            return {
                "direction": "neutral",
                "confidence": 0.3,
                "reasoning": "七步验证链数据不足，无法给出明确判断",
                "signals": [],
                "reasoning_steps": reasoning_steps,
            }

        # 计算综合信号
        net_signal = b_weight - r_weight
        max_signal = total

        # 置信度 = |net| / total，范围 0.3~0.9
        confidence = max(0.3, min(0.9, abs(net_signal) / max_signal * 0.9 + 0.1))

        # 方向
        if net_signal > 0:
            direction = "bullish"
            reasoning = f"七步验证链综合评分：看多{b_cnt}项 vs 看空{r_cnt}项，净信号+{net_signal:.1f}，利润质量总体良好"
        elif net_signal < 0:
            direction = "bearish"
            reasoning = f"七步验证链综合评分：看多{b_cnt}项 vs 看空{r_cnt}项，净信号{net_signal:.1f}，存在{abs(r_cnt)}项风险信号"
        else:
            direction = "neutral"
            reasoning = f"七步验证链综合评分：看多{b_cnt}项 vs 看空{r_cnt}项，信号均衡，等待更多信息"

        # 汇总信号列表
        signals = []
        for s in reasoning_steps:
            if s.get("status") != "neutral":
                signals.append(f"[{s['icon']}] {s['name']}：{s.get('signal', '待确认')}")

        return {
            "direction": direction,
            "confidence": confidence,
            "reasoning": reasoning,
            "signals": signals,
            "reasoning_steps": reasoning_steps,
        }

    # ── 七步具体实现 ──────────────────────────────────

    def _step1_cash(self, income_data: dict, cashflow_data: dict) -> dict:
        """第一步：看现金 — 利润是不是被现金撑住"""
        net_profit  = self._safe_float(income_data.get("PARENT_NETPROFIT", 0))
        cash_flow   = self._safe_float(cashflow_data.get("NETCASH_OPERATE", 0))
        sales_cash  = self._safe_float(cashflow_data.get("SALES_SERVICES", 0))
        revenue      = self._safe_float(income_data.get("TOTAL_OPERATE_INCOME", 0))

        details = []
        status  = "neutral"
        signal  = ""
        weight  = 1.5  # 第一步权重最高

        if net_profit == 0:
            details.append(f"归母净利润=0（无法计算）")
            signal = "净利润为0"
            status = "neutral"
        else:
            ratio = cash_flow / abs(net_profit)
            details.append(f"经营现金流={self._fmt(cash_flow)}，归母净利润={self._fmt(net_profit)}")
            details.append(f"经营现金流/净利润 = {ratio:.2f}")

            if ratio > 1.2:
                status = "bullish"
                signal = f"现金流比率{ratio:.2f}>1.2，利润质量优秀"
            elif ratio < 0.8:
                status = "bearish"
                signal = f"现金流比率{ratio:.2f}<0.8，利润质量存疑"
            else:
                status = "neutral"
                signal = f"现金流比率{ratio:.2f}处于合理区间"

        # 销售收现比
        if revenue > 0:
            sale_ratio = sales_cash / revenue
            details.append(f"销售收现/营收 = {sale_ratio:.2f}")
            if sale_ratio < 0.8:
                if status != "bearish":
                    status = "bearish"
                signal += f"，销售收现比{sale_ratio:.2f}<0.8"
        elif sales_cash > 0:
            sale_ratio = 1.0
            details.append("无法计算销售收现比（营收为0）")

        return {
            "step": 1,
            "name": "看现金",
            "icon": "💰",
            "description": "利润是不是被现金撑住",
            "status": status,
            "signal": signal,
            "details": details,
            "weight": weight,
        }

    def _step2_demand(self, balance_data: dict, cashflow_data: dict,
                      income_data: dict) -> dict:
        """第二步：看需求 — 营运资本位置"""
        ar         = self._safe_float(balance_data.get("ACCOUNTS_RECE", 0))
        inventory  = self._safe_float(balance_data.get("INVENTORY", 0))
        sales_cash = self._safe_float(cashflow_data.get("SALES_SERVICES", 0))
        revenue    = self._safe_float(income_data.get("TOTAL_OPERATE_INCOME", 0))

        details = []
        status  = "neutral"
        signal  = ""

        # 应收和收现综合判断
        if revenue > 0:
            ar_ratio = ar / revenue
            details.append(f"应收账款/营收 = {ar_ratio:.2f}（应收占总营收比）")
            if ar_ratio < 0.5:
                status = "bullish"
                signal = f"应收账款占比{ar_ratio:.2f}较低，需求真实"
            elif ar_ratio > 1.5:
                status = "bearish"
                signal = f"应收账款占比{ar_ratio:.2f}过高，存在赊销风险"
            else:
                signal = f"应收账款占比{ar_ratio:.2f}处于正常范围"
        else:
            details.append("营收为0，无法计算应收比")

        if inventory > 0:
            if revenue > 0:
                inv_ratio = inventory / revenue
                details.append(f"存货/营收 = {inv_ratio:.2f}（存货占总营收比）")

        return {
            "step": 2,
            "name": "看需求",
            "icon": "📦",
            "description": "营运资本位置对不对",
            "status": status,
            "signal": signal,
            "details": details,
            "weight": 1.2,
        }

    def _step3_performance(self, balance_data: dict) -> dict:
        """第三步：看业绩 — 合同负债/预收款先行指标"""
        contract_liab = self._safe_float(balance_data.get("CONTRACT_LIAB", 0))

        details = [f"合同负债 = {self._fmt(contract_liab)}"]
        status  = "neutral"
        signal  = ""

        if contract_liab > 0:
            # 合同负债>0说明有预收订单，是积极信号
            # 但没有同比数据，只能看绝对值
            status = "bullish"
            signal = f"合同负债{self._fmt(contract_liab)}，有预收订单支撑"
        else:
            signal = "合同负债为0或无数据"

        return {
            "step": 3,
            "name": "看业绩",
            "icon": "📋",
            "description": "合同负债/预收款先行指标",
            "status": status,
            "signal": signal,
            "details": details,
            "weight": 1.0,
        }

    def _step4_capacity(self, balance_data: dict, cashflow_data: dict) -> dict:
        """第四步：看产能 — 是否已在扩产"""
        cip         = self._safe_float(balance_data.get("CIP", 0))
        fixed_asset = self._safe_float(balance_data.get("FIXED_ASSET", 0))
        capex       = self._safe_float(cashflow_data.get("CONSTRUCT_LONG_ASSET", 0))

        details = [
            f"在建工程 = {self._fmt(cip)}",
            f"固定资产 = {self._fmt(fixed_asset)}",
            f"购建固定资产支付现金 = {self._fmt(capex)}",
        ]

        # 三指标联动判断
        active_count = sum(1 for v in [cip, fixed_asset, capex] if v > 0)

        if active_count >= 2 and capex > 0:
            status = "bullish"
            signal = f"三指标联动（{active_count}项>0），真金白银在扩产"
        elif active_count >= 1:
            status = "neutral"
            signal = f"部分扩产信号（{active_count}项>0）"
        else:
            status = "neutral"
            signal = "未检测到明显扩产信号"

        return {
            "step": 4,
            "name": "看产能",
            "icon": "🏭",
            "description": "是否已在扩产",
            "status": status,
            "signal": signal,
            "details": details,
            "weight": 1.0,
        }

    def _step5_expansion(self, cashflow_data: dict) -> dict:
        """第五步：看扩张 — 资本开支力度"""
        capex = self._safe_float(cashflow_data.get("CONSTRUCT_LONG_ASSET", 0))

        details = [f"购建固定资产无形资产支付的现金 = {self._fmt(capex)}"]
        status  = "neutral"
        signal  = ""

        if capex > 1e8:  # 超过1亿
            status = "bullish"
            signal = f"资本开支{self._fmt(capex)}，扩张力度较大"
        elif capex > 0:
            status = "neutral"
            signal = f"资本开支{self._fmt(capex)}，处于维持状态"
        else:
            signal = "无资本开支记录"

        return {
            "step": 5,
            "name": "看扩张",
            "icon": "📈",
            "description": "资本开支力度",
            "status": status,
            "signal": signal,
            "details": details,
            "weight": 0.8,
        }

    def _step6_risk(self, balance_data: dict) -> dict:
        """第六步：看扩张风险 — 净债务水平"""
        short_loan = self._safe_float(balance_data.get("SHORT_LOAN", 0))
        long_loan  = self._safe_float(balance_data.get("LONG_LOAN", 0))
        monetary   = self._safe_float(balance_data.get("MONETARYFUNDS", 0))
        equity    = self._safe_float(balance_data.get("TOTAL_PARENT_EQUITY", 0))

        total_debt  = short_loan + long_loan
        net_debt    = total_debt - monetary
        details = [
            f"短期借款 = {self._fmt(short_loan)}",
            f"长期借款 = {self._fmt(long_loan)}",
            f"货币资金 = {self._fmt(monetary)}",
            f"净债务 = {self._fmt(net_debt)}",
        ]

        status = "neutral"
        signal = ""

        if net_debt < 0:
            status = "bullish"
            signal = f"净债务为负（现金充裕），风险较低"
        elif equity > 0:
            debt_ratio = net_debt / equity
            details.append(f"净债务/股东权益 = {debt_ratio:.2f}")
            if debt_ratio > 2.0:
                status = "bearish"
                signal = f"净债务率{debt_ratio:.2f}>2.0，债务压力较大"
            elif debt_ratio > 1.0:
                status = "neutral"
                signal = f"净债务率{debt_ratio:.2f}处于中等水平"
            else:
                status = "bullish"
                signal = f"净债务率{debt_ratio:.2f}<1.0，债务健康"
        else:
            signal = f"总借款{self._fmt(total_debt)}，但无法计算债务率（股东权益为0）"

        return {
            "step": 6,
            "name": "看扩张风险",
            "icon": "⚠️",
            "description": "净债务水平",
            "status": status,
            "signal": signal,
            "details": details,
            "weight": 1.2,
        }

    def _step7_interest(self, income_data: dict) -> dict:
        """第七步：看利率敏感度 — 财务费用侵蚀"""
        finance_exp  = self._safe_float(income_data.get("FINANCE_EXPENSE", 0))
        operate_prof = self._safe_float(income_data.get("OPERATE_PROFIT", 0))

        details = [
            f"财务费用 = {self._fmt(finance_exp)}",
            f"营业利润 = {self._fmt(operate_prof)}",
        ]
        status = "neutral"
        signal = ""

        if operate_prof > 0:
            ratio = finance_exp / operate_prof
            details.append(f"财务费用/营业利润 = {ratio:.1%}")
            if ratio > 0.2:
                status = "bearish"
                signal = f"财务费用侵蚀{ratio:.1%}>20%，高风险"
            elif ratio > 0.1:
                status = "neutral"
                signal = f"财务费用侵蚀{ratio:.1%}（10%-20%），需监控"
            else:
                status = "bullish"
                signal = f"财务费用侵蚀{ratio:.1%}<10%，相对安全"
        elif finance_exp > 0:
            status = "bearish"
            signal = "营业利润为负但仍有财务费用支出，风险较高"
        else:
            signal = "财务费用和营业利润均为0，无法评估"

        return {
            "step": 7,
            "name": "看利率敏感度",
            "icon": "🏦",
            "description": "财务费用侵蚀",
            "status": status,
            "signal": signal,
            "details": details,
            "weight": 1.0,
        }

    def _fmt(self, val: float) -> str:
        """格式化金额（亿为单位）"""
        if abs(val) >= 1e8:
            return f"{val/1e8:.2f}亿"
        elif abs(val) >= 1e4:
            return f"{val/1e4:.2f}万"
        elif val == 0:
            return "0"
        else:
            return f"{val:.2f}"

    def _safe_float(self, val) -> float:
        """安全转换为 float"""
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    # ── 封装 Signal ─────────────────────────────────────────

    def _build_signal(self, result: dict, stock_code: str) -> Signal:
        """把 LLM / 规则引擎的输出封装成标准 Signal"""
        direction  = result.get("direction", "neutral")
        confidence = result.get("confidence", 0.5)
        reasoning  = result.get("reasoning", "")
        signals    = result.get("signals", [])
        reasoning_steps = result.get("reasoning_steps", [])

        meta = {
            "agent": "FinancialReportAgent",
            "reasoning_steps": reasoning_steps,
        }

        if direction == "bullish":
            return bullish_signal(
                confidence=confidence,
                reasoning=reasoning,
                signals=signals,
                source=self.name,
                stock_code=stock_code,
                signal_type="financial",
                meta=meta,
            )
        elif direction == "bearish":
            return bearish_signal(
                confidence=confidence,
                reasoning=reasoning,
                signals=signals,
                source=self.name,
                stock_code=stock_code,
                signal_type="financial",
                meta=meta,
            )
        else:
            return neutral_signal(
                confidence=confidence,
                reasoning=reasoning or "无法确定明确方向",
                source=self.name,
                stock_code=stock_code,
                signal_type="financial",
                meta=meta,
            )
