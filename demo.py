"""自检：python demo.py（数学校验器不联网、不装 openai 也能跑）。"""
import json
import os
import sys
from fractions import Fraction

sys.stdout.reconfigure(encoding="utf-8")

from core import eval_math, verify_answer

# 数学校验器自检（纯 Python，先跑通这部分）
assert eval_math("1/2 + 1/3") == Fraction(5, 6)
assert eval_math("(35 + 27) * 2") == 124
assert eval_math("0.1 + 0.2") == Fraction(3, 10)
assert verify_answer("1/2 + 1/3", "5/6") is True
assert verify_answer("1/2 + 1/3", "4/6") is False
assert verify_answer("0.1 + 0.2", "0.3") is True
assert verify_answer("3 * 7", "21") is True
print("数学校验器自检通过 OK")

if os.getenv("ZHIPU_API_KEY") or os.getenv("DASHSCOPE_API_KEY"):
    from core import diagnose

    print(json.dumps(diagnose("小明做 35 + 27 = 52", "52"), ensure_ascii=False, indent=2))
else:
    print("未检测到 API key，跳过真实诊断。设 ZHIPU_API_KEY 后重跑即可。")
