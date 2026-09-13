"""智学错题助手 — Streamlit 界面。运行：streamlit run app.py"""
import base64
import json
import os
import urllib.parse

import pandas as pd
import streamlit as st

import db
import review
from core import (
    diagnose,
    generate_similar_verified,
    check_answer,
    extract_question,
    tutor_chat_stream,
    analyze_weaknesses,
    habit_profile,
    parent_report,
)

st.set_page_config(page_title="智学错题助手", page_icon="📚", layout="wide")
db.init_db()

# ---- PWA：图标 + manifest + meta（移动端「添加到主屏幕」即可像 App 使用） ----
_BASE = os.path.dirname(os.path.abspath(__file__))


def _icon_uri(name):
    with open(os.path.join(_BASE, name), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


_manifest = {
    "name": "智学错题助手",
    "short_name": "错题助手",
    "description": "AI 错题诊断与智能复习",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": "#4A7DFF",
    "icons": [
        {"src": _icon_uri("icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": _icon_uri("icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
    ],
}
_manifest_uri = "data:application/json," + urllib.parse.quote(
    json.dumps(_manifest, ensure_ascii=False)
)

st.markdown(
    f"""
    <link rel="manifest" href="{_manifest_uri}">
    <meta name="theme-color" content="#4A7DFF">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="错题助手">
    <link rel="apple-touch-icon" href="{_icon_uri('icon-192.png')}">
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .block-container {
        max-width: 900px;
        padding-top: 1.8rem;
        padding-bottom: 3rem;
    }

    h1 {
        background: linear-gradient(90deg, #4A7DFF, #8B5CF6);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #4A7DFF, #8B5CF6);
        border: none;
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #f7f9ff, #f3f0ff);
        border: 1px solid #e9e7f5;
        border-radius: 14px;
        padding: 0.6rem 0.9rem;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px;
    }

    @media (max-width: 640px) {
        .block-container {
            padding-top: 1rem;
            padding-left: 0.7rem;
            padding-right: 0.7rem;
        }
        h1 { font-size: 1.55rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_weaknesses(patterns_json):
    return analyze_weaknesses(json.loads(patterns_json))


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_parent_report(week, last_week, weakness_lines):
    return parent_report(week, last_week, weakness_lines)


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_habits(specifics_json):
    return habit_profile(json.loads(specifics_json))


# 孩子自述错因 → 四类错误枚举的映射
SELF_CATEGORY_MAP = {
    "概念没弄懂": "概念错误",
    "算错了": "计算错误",
    "没读懂题": "审题错误",
    "不会方法": "方法错误",
}

# ---- 用户身份：每个名字一个独立错题本 ----
if "user" not in st.session_state:
    st.session_state["user"] = ""

user_id = st.session_state["user"].strip()
if not user_id:
    st.title("智学错题助手")
    st.markdown("每个人有**自己独立**的错题本，输入名字开始 👇")
    name = st.text_input("你的名字", placeholder="比如：小明")
    if st.button("进入我的错题本", type="primary", use_container_width=True):
        if name.strip():
            st.session_state["user"] = name.strip()
            st.rerun()
        else:
            st.warning("先输入你的名字哦")
    st.stop()

st.title("智学错题助手")
st.caption("拍照录错题 → AI 诊断错因 → 自动归类 → 遗忘曲线复习 → 同类题巩固")

uc1, uc2 = st.columns([3, 1])
uc1.markdown(f"👤 **{user_id}** 的错题本")
if uc2.button("切换用户", use_container_width=True):
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# 学习激励栏
ov = db.overview_stats(user_id)
m1, m2, m3 = st.columns(3)
m1.metric("📚 累计错题", f"{ov['total']} 道")
m2.metric("🔁 今日待复习", f"{ov['due']} 道")
m3.metric("🎯 已掌握", f"{ov['mastered']} 道")

_MODES = ["录入错题", "今日复习", "我的错题本", "学习报告", "家长周报"]
_ICONS = {"录入错题": "📝", "今日复习": "🔁", "我的错题本": "📚", "学习报告": "📊", "家长周报": "👨‍👩‍👧"}
mode = st.pills(
    "选功能",
    [f"{_ICONS[m]} {m}" for m in _MODES],
    default=f"{_ICONS[_MODES[0]]} {_MODES[0]}",
    label_visibility="collapsed",
)
mode = mode.split(" ", 1)[1]

if mode == "录入错题":
    st.subheader("📝 录入错题")

    # 存入错题本后清空题目/答案/图片
    if st.session_state.pop("clear_fields", False):
        st.session_state["q"] = ""
        st.session_state["ans"] = ""
        st.session_state["selfcat"] = "不确定"
        st.session_state["img_version"] = st.session_state.get("img_version", 0) + 1
        st.session_state.pop("last_upload_id", None)
        st.session_state.pop("img_bytes", None)
        st.session_state.pop("img_mime", None)
        st.session_state.pop("practice_q", None)
        st.session_state.pop("p_status", None)

    uploaded = st.file_uploader(
        "拍题图片（可选，上传后自动识别）",
        type=["jpg", "jpeg", "png"],
        key=f"img_{st.session_state.get('img_version', 0)}",
    )
    if uploaded is not None:
        fid = getattr(uploaded, "file_id", None) or uploaded.name
        if st.session_state.get("last_upload_id") != fid:
            st.session_state["last_upload_id"] = fid
            st.session_state["img_bytes"] = uploaded.getvalue()
            st.session_state["img_mime"] = uploaded.type
            with st.spinner("识别题目中……"):
                try:
                    text = extract_question(uploaded.getvalue(), uploaded.type)
                except Exception as e:
                    st.error(f"识别失败：{e}")
                    text = None
            if text:
                st.session_state["ocr_result"] = text
                st.rerun()

    if st.session_state.get("ocr_result"):
        st.session_state["q"] = st.session_state.pop("ocr_result")

    question = st.text_area("题目", key="q", placeholder="例：小明做 35 + 27 = 52")
    student_answer = st.text_input("你的错误答案", key="ans", placeholder="52")
    self_choice = st.selectbox(
        "我觉得我错在哪儿？",
        ["不确定", "概念没弄懂", "算错了", "没读懂题", "不会方法"],
        key="selfcat",
    )

    if st.button("AI 诊断", type="primary") and question and student_answer:
        with st.spinner("诊断中……"):
            try:
                st.session_state["diag"] = diagnose(
                    question,
                    student_answer,
                    image_bytes=st.session_state.get("img_bytes"),
                    image_mime=st.session_state.get("img_mime", "image/jpeg"),
                )
                st.session_state["msgs"] = []
                st.session_state["self_choice"] = self_choice
                st.session_state.pop("practice_q", None)
                st.session_state.pop("p_status", None)
            except Exception as e:
                st.error(f"AI 诊断失败：{e}")

    diag = st.session_state.get("diag")
    if diag:
        with st.container(border=True):
            st.markdown(f"**错因**：{diag['error_category']} —— {diag['error_specific']}")
            chosen = st.session_state.get("self_choice", "不确定")
            if chosen in SELF_CATEGORY_MAP:
                guessed = SELF_CATEGORY_MAP[chosen]
                if guessed == diag.get("error_category"):
                    st.success(f"你猜对了！AI 也觉得是「{chosen}」")
                else:
                    st.warning(
                        f"你说「{chosen}」，AI 觉得是「{diag.get('error_category')}」"
                        "—— 差在哪儿呢？"
                    )
            st.markdown(f"**题型**：{diag['category']} / {diag['knowledge_point']}")
            st.markdown(f"**正确答案**：{diag['correct_answer']}")
            st.markdown("**解题步骤**：" + diag.get("correct_steps", ""))
            st.markdown(f"**纠正建议**：{diag['explanation']}")

        # 学练闭环：一键做同类题
        if st.button("🎯 做一道同类题巩固", key="practice_btn"):
            with st.spinner("出题中……"):
                try:
                    st.session_state["practice_q"] = generate_similar_verified(
                        question, diag.get("knowledge_point", "")
                    )
                except Exception as e:
                    st.error(f"出题失败：{e}")

        practice = st.session_state.get("practice_q")
        if practice:
            with st.container(border=True):
                st.markdown("**同类题**：" + practice["question"])
                v = practice.get("verified")
                if v is True:
                    st.caption("✓ 答案已通过验算")
                elif v is False:
                    st.caption("（答案校验未通过，仅供参考）")
                else:
                    st.caption("（文字题未验算）")
                p_ans = st.text_input("你的答案", key="p_ans")
                if st.button("提交答案", key="p_sub"):
                    st.session_state["p_status"] = (
                        "correct" if check_answer(practice["answer"], p_ans) else "wrong"
                    )
                p_status = st.session_state.get("p_status")
                if p_status == "correct":
                    st.success("太棒了，答对啦 🎉")
                    if st.button("再来一道", key="p_again"):
                        st.session_state.pop("practice_q", None)
                        st.session_state.pop("p_status", None)
                        st.rerun()
                elif p_status == "wrong":
                    st.error("再想想哦～")
                    if st.checkbox("看答案", key="p_view"):
                        st.write("正确答案：", practice["answer"])

        st.divider()
        st.subheader("没懂？继续问老师，直到你明白")
        msgs = st.session_state.get("msgs", [])
        for m in msgs:
            st.chat_message(m["role"]).write(m["content"])
        follow = st.chat_input("比如：为什么这里要进位？")
        if follow:
            msgs.append({"role": "user", "content": follow})
            st.chat_message("user").write(follow)
            with st.chat_message("assistant"):
                try:
                    reply = st.write_stream(
                        tutor_chat_stream(question, student_answer, diag, msgs)
                    )
                except Exception as e:
                    st.error(f"老师暂时无法回答：{e}")
                    st.stop()
            msgs.append({"role": "assistant", "content": reply})
            st.session_state["msgs"] = msgs

        if st.button("我明白了，存入错题本", type="primary"):
            chosen = st.session_state.get("self_choice", "不确定")
            self_category = SELF_CATEGORY_MAP.get(chosen)
            calibration = None
            if self_category:
                calibration = 1 if self_category == diag.get("error_category") else 0
            db.add_mistake(user_id, diag, question, student_answer, self_category, calibration)
            st.session_state.pop("diag")
            st.session_state.pop("msgs", None)
            st.session_state.pop("self_choice", None)
            st.session_state["clear_fields"] = True
            st.rerun()

elif mode == "今日复习":
    st.subheader("🔁 今日待复习")
    due = db.due_today(user_id)
    if not due:
        st.info("今天没有要复习的错题")
    for m in due:
        with st.expander(f"#{m['id']} · {m['knowledge_point']}"):
            st.write(m["question"])
            st.caption(f"上次错答：{m['student_answer']}")

            ans = st.text_input("你的答案", key=f"ain{m['id']}")
            col1, col2 = st.columns(2)
            if col1.button("提交", key=f"sub{m['id']}"):
                if check_answer(m["correct_answer"], ans):
                    r, i, e = review.sm2(5, m["repetition"], m["interval"], m["ease"])
                    db.update_review(user_id, m["id"], r, i, e)
                    st.success("答对了！")
                    st.rerun()
                else:
                    st.error("不对，再想想")
            if col2.button("还是不会", key=f"no{m['id']}"):
                r, i, e = review.sm2(0, m["repetition"], m["interval"], m["ease"])
                db.update_review(user_id, m["id"], r, i, e)
                st.rerun()

            if st.checkbox("看答案", key=f"ans{m['id']}"):
                st.write("正确答案：", m["correct_answer"])

            if st.button("出同类题巩固", key=f"sim{m['id']}"):
                with st.spinner("生成中……"):
                    try:
                        st.session_state[f"sim_{m['id']}"] = generate_similar_verified(
                            m["question"], m["knowledge_point"]
                        )
                    except Exception as e:
                        st.error(f"生成失败：{e}")

            sim = st.session_state.get(f"sim_{m['id']}")
            if sim:
                st.write("同类题：", sim["question"])
                v = sim.get("verified")
                if v is True:
                    st.caption("✓ 答案已通过独立数学验算")
                elif v is False:
                    st.caption("（答案校验未通过，仅供参考）")
                else:
                    st.caption("（文字题无算式，未做机器验算）")
                sim_ans = st.text_input("你的答案", key=f"simans{m['id']}")
                if st.button("提交答案", key=f"simsub{m['id']}"):
                    st.session_state[f"sim_status_{m['id']}"] = (
                        "correct" if check_answer(sim["answer"], sim_ans) else "wrong"
                    )
                status = st.session_state.get(f"sim_status_{m['id']}")
                if status == "correct":
                    st.success("答对了！")
                    if st.button("清除题目，再来一道", key=f"simclear{m['id']}"):
                        st.session_state.pop(f"sim_{m['id']}", None)
                        st.session_state.pop(f"sim_status_{m['id']}", None)
                        st.rerun()
                elif status == "wrong":
                    st.error("不对，再想想")
                    if st.checkbox("查看答案", key=f"simview{m['id']}"):
                        st.write("正确答案：", sim["answer"])

elif mode == "我的错题本":
    st.subheader("📚 我的错题本")
    stats = db.category_stats(user_id)
    if not stats:
        st.info("还没有错题，先去「录入错题」")
    else:
        cols = st.columns(len(stats))
        for col, row in zip(cols, stats):
            col.metric(row["category"] or "未分类", f"{row['n']} 题")

        cats = ["全部"] + [(s["category"] or "未分类") for s in stats]
        chosen = st.selectbox("按类目筛选", cats)
        items = db.all_mistakes(user_id, None if chosen == "全部" else chosen)
        for m in items:
            with st.expander(
                f"#{m['id']} · {m['category'] or '未分类'} · {m['knowledge_point']}"
            ):
                st.write(m["question"])
                st.caption(
                    f"错答：{m['student_answer']} · 错因：{m['error_specific']} · 答案：{m['correct_answer']}"
                )
                if st.button("重做这道题", key=f"redo{m['id']}"):
                    st.session_state[f"redo_{m['id']}"] = True
                if st.session_state.get(f"redo_{m['id']}"):
                    redo_ans = st.text_input("你的答案", key=f"redoans{m['id']}")
                    if st.button("提交", key=f"redosub{m['id']}"):
                        st.session_state[f"redo_status_{m['id']}"] = (
                            "correct" if check_answer(m["correct_answer"], redo_ans) else "wrong"
                        )
                    status = st.session_state.get(f"redo_status_{m['id']}")
                    if status == "correct":
                        st.success("答对了！")
                    elif status == "wrong":
                        st.error("不对，再想想")
                        if st.checkbox("查看答案", key=f"redoview{m['id']}"):
                            st.write("正确答案：", m["correct_answer"])
                if st.button("删除这道题", key=f"del{m['id']}"):
                    db.delete_mistake(user_id, m["id"])
                    st.rerun()

elif mode == "学习报告":
    st.subheader("📊 学习报告")
    if not db.category_stats(user_id):
        st.info("还没有错题，先去「录入错题」")
    else:
        st.markdown("### 你有多了解自己")
        cs = db.calibration_stats(user_id)
        if cs:
            df0 = pd.DataFrame(
                [(r["d"], r["ok"] / r["total"]) for r in cs if r["total"]],
                columns=["日期", "猜对比例"],
            ).set_index("日期")
            st.line_chart(df0)
            st.caption("你猜自己错在哪儿的准确率，越往上说明越了解自己")
        else:
            st.caption("录错题时选「我觉得我错在哪儿」，就能看到这条曲线")

        st.markdown("### 错因分布")
        es = db.error_stats(user_id)
        if es:
            df = pd.DataFrame(
                [(r["error_category"] or "未分类", r["n"]) for r in es],
                columns=["错因", "次数"],
            ).set_index("错因")
            st.bar_chart(df)

        st.markdown("### 薄弱知识点")
        ks = db.knowledge_stats(user_id)
        if ks:
            df2 = pd.DataFrame(
                [(r["knowledge_point"] or "未分类", r["n"]) for r in ks],
                columns=["知识点", "次数"],
            ).set_index("知识点")
            st.bar_chart(df2)

        st.markdown("### AI 薄弱点诊断")
        patterns = db.weak_patterns(user_id, threshold=2)
        with st.spinner("分析中……"):
            try:
                st.write(_cached_weaknesses(
                    json.dumps([dict(p) for p in patterns], ensure_ascii=False)
                ))
            except Exception as e:
                st.error(f"分析失败：{e}")

        st.markdown("### 错误习惯画像")
        specs = db.specific_error_stats(user_id)
        with st.spinner("归纳中……"):
            try:
                st.write(_cached_habits(
                    json.dumps([dict(s) for s in specs], ensure_ascii=False)
                ))
            except Exception as e:
                st.error(f"归纳失败：{e}")

else:
    st.subheader("👨‍👩‍👧 家长周报")
    if not db.category_stats(user_id):
        st.info("还没有错题，先去「录入错题」")
    else:
        week = db.count_since(user_id, 7)
        last_week = db.count_between(user_id, 14, 7)
        c1, c2 = st.columns(2)
        c1.metric("本周错题", f"{week} 道")
        c2.metric("上周错题", f"{last_week} 道")
        if week < last_week:
            st.success("本周错题比上周少，在进步")
        elif week > last_week:
            st.warning("本周错题比上周多，需要关注")
        else:
            st.info("本周和上周错题数持平")

        ks = db.knowledge_stats(user_id)
        weak_lines = "、".join(f"{r['knowledge_point']}（{r['n']}道）" for r in ks[:5]) or "暂无"
        st.markdown("### AI 家长版总结")
        with st.spinner("生成中……"):
            try:
                st.write(_cached_parent_report(week, last_week, weak_lines))
            except Exception as e:
                st.error(f"生成失败：{e}")
