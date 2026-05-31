#!/usr/bin/env python3
"""System A 测试入口 — 触发 core/system_a.py 自测"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
SKILL_DIR = REPO_ROOT / "skills" / "industry" / "industrial_sentinel"
core_dir = SKILL_DIR / "core"
sys.path.insert(0, str(SKILL_DIR))

# 直接执行 core/system_a.py 的 if __name__ == '__main__' 块
import runpy
runpy.run_path(str(core_dir / "system_a.py"), run_name="__main__")
