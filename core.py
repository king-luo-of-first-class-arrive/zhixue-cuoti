"""智学错题助手核心：错因诊断、同类题生成、确定性答案校验、讲解、拍照识别。"""
import ast
import base64
import json
import os
import re
from fractions import Fraction

import taxonomy

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import sympy
except ImportError:
    sympy = None


def _load_dotenv():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v.strip())
    except FileNotFoundError:
        pass


_load_dotenv()

MODEL = os.getenv("AI_MODEL", "glm-4-flash")
VISION_MODEL = os.getenv("VISION_MODEL", "glm-4v-flash")

_API_KEY = os.getenv("ZHIPU_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
_client = (
    OpenAI(
        api_key=_API_KEY,
        base_url=os.getenv("AI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
        timeout=60.0,
        max_retries=2,
    )
    if OpenAI is not None and _API_KEY
    else None
)


# ---- ① 错因诊断 ----
DIAGNOSE_PROMPT = """你是小学数学老师，分析学生做错题的具体原因。

题目：{question}
学生的错误答案：{student_answer}
{self_note}题型分类表（一级领域 → 二级题型）：
{taxonomy}

分类规则：按题目考查的知识点分类，不要按运算符号分类。
- 有具体人物/物品、问「一共/还剩/相差/每份」的题属于「应用题」；
- 「X单位=多少Y单位」的换算题属于「单位换算」；
- 光秃秃算式没有情境的才属于「计算」。
例如「长方形长5米宽3米求面积」属于「图形/算面积」，「直角是多少度」属于「图形/角」，「小明买5本书每本3元一共多少元」属于「应用题/乘除法应用题」，「甲有12个苹果比乙多5个，乙有几个」属于「应用题/加减法应用题」，「一段路长120千米走了1/4，走了多少千米」属于「应用题/分数应用题」，「3米=多少厘米」属于「单位换算/长度单位」，「1小时=多少分钟」属于「单位换算/时间单位」，「5元=多少角」属于「单位换算/人民币」，「1/2+1/3」属于「计算/分数计算」，「问1/2表示什么意思」才属于「数的认识」。

解题步骤（correct_steps）按题型套用下面的标准写法，每一步写成小学生看得懂的白话，用「先…再…最后…」串起来。模板里的例子只示范格式，要按题目的实际数字重新写，禁止照抄例子里的题目和数字：
{templates}
禁止把数字和运算符拆成单个字符，比如 1+1 写「1+1=2」，绝不能写「1;+;1;=;2」。

只输出一个 JSON，不要输出任何其他文字：
{{
  "category": "一级领域，按考查知识点从分类表选一个",
  "knowledge_point": "二级题型，从所选领域对应的题型里选一个，文字必须和分类表一模一样，不要缩写或改写",
  "error_category": "概念错误|计算错误|审题错误|方法错误 之一",
  "error_specific": "学生具体错在哪，如'进位时忘记加1'，禁止用'粗心'这种空泛说法",
  "correct_answer": "正确答案，必须和解题步骤最后算出的结果一致",
  "expression": "算出 correct_answer 的完整计算式或方程（结果必须等于 correct_answer，不能只写中间步骤，如平均数要写 (4+6+8+10)/4 而不是 4+6+8+10）。纯算式不带等号，方程含 x 和 =（如 2*x-x=6）；纯文字题没有算式就写空字符串",
  "correct_steps": "按上面「解题步骤写法」生成",
  "explanation": "针对该错误的一句话纠正建议"
}}"""


def diagnose(question, student_answer, self_note=None, image_bytes=None, image_mime="image/jpeg"):
    if self_note and self_note.strip():
        note_section = (
            f"学生的自述错因：{self_note.strip()}\n"
            "请结合自述交叉验证：合理就采纳并细化，与实际答案矛盾就指出真实原因，是空话就细化成具体错因。\n"
        )
    else:
        note_section = ""
    prompt = DIAGNOSE_PROMPT.format(
        question=question,
        student_answer=student_answer,
        self_note=note_section,
        taxonomy=taxonomy.format_for_prompt(),
        templates=taxonomy.format_templates(),
    )
    if image_bytes:
        prompt = "题目图片已一并提供（可能含几何图形）。请结合图片里的图形、标注、阴影等信息诊断。\n" + prompt

    def _run(p):
        if image_bytes:
            return _chat_vision_json(p, image_bytes, image_mime, temperature=0.2)
        return _chat(p, temperature=0.2)

    result = _run(prompt)

    # 独立验算正确性：expression 与 correct_answer 不一致则反馈重试
    expr = str(result.get("expression", "")).strip()
    for _ in range(2):
        ans_num = _strip_unit(result.get("correct_answer", ""))
        try:
            eval_math(ans_num)
        except (ValueError, ZeroDivisionError, SyntaxError):
            break  # 答案不是纯数字，无法验算
        if not expr or verify_answer(expr, ans_num):
            break
        result = _run(
            prompt
            + f"\n\n注意：你的 correct_answer「{result.get('correct_answer')}」与计算式「{expr}」的结果不一致，说明答案算错了。请重新独立计算，给出正确的 correct_answer 和与之匹配的 expression。"
        )
        expr = str(result.get("expression", "")).strip()

    cats = list(taxonomy.CATEGORIES)
    result["category"] = _normalize_type(result.get("category", ""), cats)
    result["knowledge_point"] = _normalize_type(
        result.get("knowledge_point", ""), taxonomy.CATEGORIES.get(result["category"], [])
    )
    return result


def _normalize_type(value, options):
    """把 AI 输出的分类归到最近的枚举值，防缩写/改写；无法匹配则归入「未分类」。"""
    if not value:
        return "未分类"
    if value in options:
        return value
    for opt in options:
        if value in opt or opt in value:
            return opt
    return "未分类"


# ---- ② 同类题生成（附带可校验算式）----
SIMILAR_PROMPT = """你是小学数学老师，根据原题和知识点出一道同类型同难度的新题。

原题：{question}
知识点：{knowledge_point}

只输出一个 JSON：
{{
  "question": "新题文字",
  "answer": "新题答案",
  "expression": "新题对应的计算式或方程，只含数字和 + - * / ( )，方程可含 x 和 =，如 (35+27) 或 2*x+3=11"
}}"""


def generate_similar(question, knowledge_point):
    return _chat(
        SIMILAR_PROMPT.format(question=question, knowledge_point=knowledge_point),
        temperature=0.7,
    )


def generate_similar_verified(question, knowledge_point, max_attempts=3):
    """出同类题并独立验证答案（不靠 LLM 自检）。验证失败则把错误反馈给模型重试。

    返回结果多一个 verified 字段：True=已通过符号引擎验算，
    None=无法验证（纯文字题无算式），False=重试后仍未通过。
    """
    feedback = ""
    r = {}
    for _ in range(max(1, max_attempts)):
        prompt = SIMILAR_PROMPT.format(question=question, knowledge_point=knowledge_point)
        if feedback:
            prompt += (
                "\n\n注意：你上次给出的答案经数学验算不成立。"
                f"{feedback} 请重新出题并确保答案与算式一致。"
            )
        r = _chat(prompt, temperature=0.7)
        expr = str(r.get("expression", "")).strip()
        ans = str(r.get("answer", "")).strip()
        if not expr:
            r["verified"] = None
            return r
        if verify_answer(expr, ans):
            r["verified"] = True
            return r
        feedback = f"表达式「{expr}」按你的答案「{ans}」验算不成立。"
    r["verified"] = False
    return r


# ---- ④ 多轮讲解（诊断后继续追问，直到学生明白）----
def _tutor_messages(question, student_answer, diag, history):
    system = (
        "你是耐心的小学数学老师，正在给一个做错题的学生讲题。\n"
        f"题目：{question}\n学生错误答案：{student_answer}\n"
        f"诊断：{json.dumps(diag, ensure_ascii=False)}\n"
        "用大白话引导他理解错在哪、为什么，别直接甩答案。"
    )
    return [{"role": "system", "content": system}] + history


def tutor_chat(question, student_answer, diag, history):
    """history: [{"role": "user"/"assistant", "content": ...}]，含最新一条用户提问。"""
    return _chat_text(_tutor_messages(question, student_answer, diag, history), temperature=0.5)


def tutor_chat_stream(question, student_answer, diag, history):
    """流式版讲解：逐 chunk 返回文本，供 st.write_stream 使用。"""
    return _stream(_tutor_messages(question, student_answer, diag, history), temperature=0.5)


# ---- ⑤ 拍照识别题目（视觉模型）----
def extract_question(image_bytes, mime="image/jpeg"):
    _require_client()
    b64 = base64.b64encode(image_bytes).decode()
    resp = _client.chat.completions.create(
        model=VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "识别图片里的数学题目，只输出题目原文，不要解题。"},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
        temperature=0.1,
    )
    return resp.choices[0].message.content


# ---- ⑥ 系统性薄弱点分析（错因归因链）----
def analyze_weaknesses(patterns):
    """输入反复出错的模式列表，AI 分析根本原因与复习建议。"""
    if not patterns:
        return "错题还不多，暂无法分析薄弱点。再多录几道错题，报告会更准。"
    lines = "\n".join(
        f"- {p['category']}/{p['knowledge_point']}：{p['error_category']}（{p['n']}次）"
        for p in patterns
    )
    prompt = (
        "你是学习诊断专家。下面是一个孩子反复出错的模式（题型/错因/次数）：\n"
        f"{lines}\n\n"
        "请分析：1）根本原因——不要只重复表面错因，找出底层没掌握的概念或习惯；"
        "2）给出 2-3 条针对性复习建议。中文，分点，200 字内。"
    )
    return _chat_text([{"role": "user", "content": prompt}], temperature=0.5)


# ---- ⑥b 错误习惯画像（从零散错因到可命名的坏习惯）----
def habit_profile(specifics):
    """输入高频具体错因，AI 归纳成 2-3 个可命名的「错误习惯」。"""
    if not specifics:
        return "还没有足够的错因记录，无法生成错误习惯画像。再多录几道错题，画像会更准。"
    lines = "\n".join(f"- {s['error_specific']}（{s['n']}次）" for s in specifics)
    prompt = (
        "你是学习诊断教练。下面是一个孩子反复出现的具体错因（含次数）：\n"
        f"{lines}\n\n"
        "请归纳成 2-3 个可命名的「错误习惯」，每个给出：1）一个孩子自己能记住的命名"
        "（如『进位漏1症』『不读单位症』）；2）证据（对应哪几条错因）；"
        "3）一条最有效的纠正方法。中文，分点，200 字内，语气像教练。"
    )
    return _chat_text([{"role": "user", "content": prompt}], temperature=0.5)


# ---- ⑦ 家长版周报 ----
def parent_report(week, last_week, weakness_lines):
    """生成家长版周报。week/last_week 本周/上周错题数，weakness_lines 薄弱点简述。"""
    prompt = (
        "你是教育顾问，给家长写孩子本周数学学习周报。\n"
        f"本周新增错题 {week} 道，上周 {last_week} 道。\n"
        f"主要错题分布：{weakness_lines}\n"
        "用家长能懂的话写：1）一句话总结；2）最需要关注的问题；"
        "3）给家长的 1-2 条可执行建议。200 字内，语气平和专业。"
    )
    return _chat_text([{"role": "user", "content": prompt}], temperature=0.5)


# ---- ③ 确定性答案校验（不靠 LLM 自检）----
_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.USub: lambda a: -a,
    ast.UAdd: lambda a: +a,
}


def eval_math(expr):
    """安全求值四则运算，返回精确分数（支持小数/分数/括号）。"""
    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            v = node.value
            return Fraction(str(v)) if isinstance(v, float) else Fraction(v)
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.operand))
        raise ValueError(f"不支持的表达式: {ast.dump(node)}")

    return _eval(ast.parse(expr, mode="eval"))


def solve_equation(eq_str, var="x"):
    """解一元方程，返回实数解列表。如 '2*x+3=11' 或 '2x=10' -> [4.0]/[5.0]。"""
    if sympy is None:
        raise RuntimeError("需要 sympy 库：pip install sympy")
    if not re.fullmatch(r"[0-9+*/=().\sx-]+", eq_str):
        raise ValueError("方程表达式包含非法字符")
    eq_str = re.sub(r"\s+", "", eq_str)
    eq_str = re.sub(r"(\d)([a-zA-Z(])", r"\1*\2", eq_str)  # 2x -> 2*x, 2( -> 2*(
    eq_str = eq_str.replace("=", "-(") + ")"
    x = sympy.symbols(var)
    expr = sympy.sympify(eq_str)
    return [float(s) for s in sympy.solve(expr, x) if s.is_real]


_UNIT_RE = re.compile(r"[米分米厘米毫米千米公里千克克吨元角分升毫升小时分钟秒个只条张本块根件次]+$")


def _strip_unit(x):
    """去掉答案里的单位后缀，供验算用。"""
    return _UNIT_RE.sub("", str(x).strip())


def verify_answer(expression, claimed_answer):
    """独立校验 LLM 声称的答案：先算术等值，再方程求解。"""
    claimed_answer = _strip_unit(claimed_answer)
    try:
        return eval_math(expression) == eval_math(claimed_answer)
    except (ValueError, ZeroDivisionError, SyntaxError):
        pass
    if "=" in expression and "x" not in expression:
        left, _, right = expression.partition("=")
        try:
            return eval_math(left) == eval_math(right)
        except (ValueError, ZeroDivisionError, SyntaxError):
            return False
    if "=" in expression or "x" in expression:
        try:
            roots = solve_equation(expression)
            claimed = str(claimed_answer).replace("x=", "").replace("x =", "").strip()
            cval = eval_math(claimed)
            return any(abs(r - float(cval)) < 1e-9 for r in roots)
        except Exception:
            return False
    return False


_CN_DIGIT = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNIT = {"十": 10, "百": 100, "千": 1000, "万": 10000}


def _cn_to_int(s):
    """中文数字转整数：五=5、十五=15、二十五=25、一百=100；含非中文数字字符返回 None。"""
    total = 0
    cur = 0
    for ch in s:
        if ch in _CN_DIGIT:
            cur = _CN_DIGIT[ch]
        elif ch in _CN_UNIT:
            u = _CN_UNIT[ch]
            if u >= 10000:
                total = (total + cur) * u
            else:
                total += (cur or 1) * u
            cur = 0
        else:
            return None
    return total + cur


def check_answer(correct, student):
    """判断学生作答是否等于正确答案：先数值等值，再字符串兜底。"""
    trans = str.maketrans("０１２３４５６７８９．－＋／（）", "0123456789.-+/()")

    def norm(x):
        x = str(x).strip().translate(trans).replace(" ", "")
        x = re.sub(r"[米分米厘米毫米千米公里千克克吨元角分升毫升小时分钟秒个只条张本块根件次]+$", "", x)
        m = re.match(r"^[a-zA-Z]=(.+)$", x)  # x=4 -> 4
        if m:
            x = m.group(1)
        if x.endswith("%"):  # 50% -> 0.5
            try:
                x = str(float(x[:-1]) / 100)
            except ValueError:
                pass
        cn = _cn_to_int(x)
        if cn is not None:
            x = str(cn)
        return x

    c, s = norm(correct), norm(student)
    if not c or not s:
        return False
    try:
        return eval_math(c) == eval_math(s)
    except (ValueError, ZeroDivisionError, SyntaxError):
        return c == s


# ---- 工具 ----
def _require_client():
    if _client is None:
        raise RuntimeError(
            "未装 openai 库或未配 API key。先 pip install openai，再设 ZHIPU_API_KEY。"
        )


def _chat(prompt, temperature):
    _require_client()
    resp = _client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return _parse_json(resp.choices[0].message.content)


def _chat_vision_json(prompt, image_bytes, mime, temperature):
    """用视觉模型看图 + 文字，返回 JSON。用于带图的错因诊断。"""
    _require_client()
    b64 = base64.b64encode(image_bytes).decode()
    resp = _client.chat.completions.create(
        model=VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
        temperature=temperature,
    )
    return _parse_json(resp.choices[0].message.content)


def _chat_text(messages, temperature):
    _require_client()
    resp = _client.chat.completions.create(
        model=MODEL, messages=messages, temperature=temperature
    )
    return resp.choices[0].message.content


def _stream(messages, temperature):
    """流式返回文本 chunk，供 st.write_stream 使用。"""
    _require_client()
    resp = _client.chat.completions.create(
        model=MODEL, messages=messages, temperature=temperature, stream=True
    )
    for chunk in resp:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def _parse_json(text):
    text = text.strip()
    # 去掉可能的 markdown 代码块围栏
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"AI 输出不含 JSON: {text[:200]}")
    return json.loads(text[start:end + 1])
