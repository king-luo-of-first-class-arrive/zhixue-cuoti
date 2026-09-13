"""生成「智学错题助手」项目说明 PDF（iCAN 竞赛交付物，≤20页）。"""
import os
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)

# ---- 字体 ----
FONT_DIR = "C:/Windows/Fonts"
for name, path in [("hei", "simhei.ttf"), ("msyh", "msyh.ttc")]:
    p = os.path.join(FONT_DIR, path)
    if os.path.exists(p):
        try:
            pdfmetrics.registerFont(TTFont(name, p, subfontIndex=0))
        except Exception:
            pdfmetrics.registerFont(TTFont(name, p))
    else:
        raise RuntimeError(f"缺少字体 {p}")

BODY_FONT = "msyh"
HEAD_FONT = "hei"

# ---- 样式 ----
PRIMARY = colors.HexColor("#4A7DFF")
DARK = colors.HexColor("#2b2b2b")
GRAY = colors.HexColor("#555555")

cover_title = ParagraphStyle("cover_title", fontName=HEAD_FONT, fontSize=34, leading=44,
                             textColor=DARK, alignment=TA_CENTER)
cover_sub = ParagraphStyle("cover_sub", fontName=BODY_FONT, fontSize=16, leading=24,
                           textColor=PRIMARY, alignment=TA_CENTER)
cover_meta = ParagraphStyle("cover_meta", fontName=BODY_FONT, fontSize=11, leading=18,
                            textColor=GRAY, alignment=TA_CENTER)

h1 = ParagraphStyle("h1", fontName=HEAD_FONT, fontSize=16, leading=23, textColor=PRIMARY,
                    spaceBefore=13, spaceAfter=7)
h2 = ParagraphStyle("h2", fontName=HEAD_FONT, fontSize=12, leading=17, textColor=DARK,
                    spaceBefore=8, spaceAfter=3)
body = ParagraphStyle("body", fontName=BODY_FONT, fontSize=10.5, leading=17, textColor=DARK,
                      spaceAfter=5)
bullet = ParagraphStyle("bullet", fontName=BODY_FONT, fontSize=10.5, leading=16, textColor=DARK,
                        leftIndent=14, bulletIndent=4, spaceAfter=2)

W, H = A4
PAGE_MARGIN = 1.9 * cm


def p(text, style=body):
    return Paragraph(text, style)


def b(text):
    return Paragraph(text, bullet, bulletText="•")


def table(data, widths, header=True, fontsize=9):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), BODY_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), fontsize),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), HEAD_FONT),
        ]
    t.setStyle(TableStyle(style))
    return t


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont(BODY_FONT, 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(PAGE_MARGIN, 1.1 * cm, "智学错题助手 · 项目说明")
    canvas.drawRightString(W - PAGE_MARGIN, 1.1 * cm, f"第 {doc.page} 页")
    canvas.restoreState()


story = []

# ================= 封面 =================
story.append(Spacer(1, 3.2 * cm))
story.append(p("智学错题助手", cover_title))
story.append(Spacer(1, 0.5 * cm))
story.append(p("AI 驱动的小学数学错题诊断与智能复习系统", cover_sub))
story.append(Spacer(1, 1.6 * cm))
story.append(HRFlowable(width="60%", thickness=1, color=PRIMARY, hAlign="CENTER"))
story.append(Spacer(1, 1.6 * cm))
story.append(p("iCAN 大学生创新创业大赛 · AI 应用创新挑战赛", cover_meta))
story.append(p("软件赛道 · 参赛作品", cover_meta))
story.append(Spacer(1, 0.4 * cm))
story.append(p("2026 年 9 月", cover_meta))
story.append(PageBreak())

# ================= 一、项目背景 =================
story.append(p("一、项目背景", h1))
story.append(p(
    "随着「双减」政策的持续推进，小学阶段的校外学科培训大幅压减，孩子的课后学习与辅导责任更多地回归家庭。"
    "然而，多数家长既缺乏系统的学科辅导能力，也缺少充足的时间与精力。小学数学作为数理思维启蒙的关键阶段，"
    "一道错题背后往往对应着一个未掌握的知识点或一个不良的解题习惯，是查漏补缺中最具价值的资源。"))
story.append(p(
    "但现实中，错题管理长期停留在「手抄错题本」与「拍照存档」两种原始方式：手抄费时费力、难以坚持；"
    "拍照存档只是把错题「堆积」起来，无法回答家长和学生最关心的三个问题——<b>这道题为什么错、下次如何不再错、什么时候该复习</b>。"
    "市面主流的搜题软件虽能「搜到答案」，却普遍被诟病「只给答案、不讲错因」「AI 答得一塌糊涂」，难以承担起真正的诊断与辅导职能。"))
story.append(p(
    "与此同时，大语言模型（LLM）与多模态视觉模型在近两年快速成熟，为「错因智能诊断」这一长期难题提供了全新的技术可能。"
    "本项目即是在这一背景下，面向小学数学这一最大基数、最需打基础的学段，"
    "将 AI 能力与教育科学规律（遗忘曲线、元认知理论）深度融合，打造一款「录题即诊断、诊断即复习」的智能错题助手。"))

# ================= 二、痛点分析 =================
story.append(p("二、痛点分析", h1))
story.append(p(
    "为准确识别真实需求，团队对作业帮、小猿搜题、蜜蜂试卷、洋葱学园、今知错题本等主流产品进行了深入调研，"
    "系统梳理了 B 站、知乎、应用商店的用户评价。调研中，用户对搜题软件最尖锐的批评集中在「AI 答得一塌糊涂」"
    "「拍到的题要么对不上答案、要么题型错误」「单图多题识别就会出错、解析跑不出来」。据此归纳出五大核心痛点："))

story.append(p("痛点 1：错题整理耗时低效", h2))
story.append(b("手抄一道错题平均需 2~3 分钟，学生极易半途而废；多数工具虽支持拍照录入，但停留在「拍照存图」层面，缺乏结构化处理与归类，错题本最终沦为「收藏夹」。"))
story.append(p("痛点 2：只抄答案、不理解错因", h2))
story.append(b("搜题软件本质是「给答案」，学生复制答案却不理解错在哪，同类错误反复出现。有用户直言「如果你只看答案，那它就是一个抄答案的工具」。"))
story.append(p("痛点 3：错因无法精准定位", h2))
story.append(b("家长和学生只知道「做错了」，却说不清是概念没懂、计算失误、审题不清还是方法不会，只能笼统归为「粗心」，无法对症下药。"))
story.append(p("痛点 4：复习缺乏科学规划", h2))
story.append(b("错题本「只整理、不复盘」是普遍现象——不知道何时该重做哪道题，靠感觉复习，既容易遗忘又可能无效重复。"))
story.append(p("痛点 5：家长存在信息盲区", h2))
story.append(b("家长难以持续、客观地了解孩子的薄弱知识点与进步轨迹，只能依赖考试成绩这一滞后信号，错过最佳干预时机。"))

# ================= 三、竞品分析 =================
story.append(p("三、竞品分析与差异化定位", h1))
story.append(p(
    "调研显示，市面主流产品各有侧重但均存在明显短板，本作品正是针对这些短板进行差异化设计："))
story.append(table(
    [
        ["维度", "作业帮", "小猿搜题", "蜜蜂试卷", "洋葱学园", "本作品"],
        ["题库/内容", "19亿题库", "30亿题库", "错题组卷", "动画微课", "AI生成+校验"],
        ["错因诊断", "自动标错因", "五维错因", "较弱", "讲题为主", "精准四类+具体错点"],
        ["答案可信度", "依赖题库", "依赖题库", "一般", "一般", "符号引擎独立验算"],
        ["元认知训练", "无", "无", "无", "无", "有（自评对照）"],
        ["同类题", "有(题库)", "无", "被诟病", "配题", "生成即验证"],
        ["广告/付费", "广告多", "会员贵", "需会员", "会员墙", "免费无广告"],
    ],
    widths=[2.6 * cm, 2.6 * cm, 2.6 * cm, 2.6 * cm, 2.6 * cm, 3.2 * cm],
    fontsize=8.5,
))
story.append(Spacer(1, 0.3 * cm))
story.append(p(
    "可见，作业帮、小猿搜题的核心优势在「海量题库」，但其答案依赖题库匹配，遇到新题、自编题即失效；"
    "蜜蜂试卷强在试卷擦除，但「讲题弱、举一反三被诟病」；洋葱学园强在动画微课，但以「内容」而非「诊断」为核心。"
    "本作品则以「AI 错因诊断 + 确定性答案校验 + 元认知训练」形成差异化壁垒，聚焦「教孩子为什么错」，而非「给答案」。"))

# ================= 四、需求分析 =================
story.append(p("四、需求分析", h1))
story.append(p("4.1 功能需求", h2))
story.append(b("智能录入：支持拍照识别题目、自动提取题干，降低录入门槛。"))
story.append(b("错因诊断：对每道错题输出「错因分类 + 具体错点 + 正确答案 + 分步解析 + 纠正建议」。"))
story.append(b("自动归类：按小学数学知识体系（一级领域 → 二级题型）自动归档。"))
story.append(b("科学复习：基于遗忘曲线安排复习时机，实现「该复习时才出现」。"))
story.append(b("同类题巩固：针对薄弱点自动生成同难度同类题，实现「练会为止」。"))
story.append(b("学情反馈：生成学习报告、错误习惯画像与家长周报，让进步可量化。"))
story.append(p("4.2 非功能需求", h2))
story.append(b("易用性：界面面向小学生，操作步骤少、反馈直观、无专业术语。"))
story.append(b("多端适配：响应式布局支持手机/平板/电脑，并可安装为 PWA。"))
story.append(b("数据隔离：多用户数据互相隔离，每个学生拥有独立错题本。"))
story.append(b("答案可信：AI 生成的题目与答案需经过确定性校验，杜绝「AI 乱答」。"))
story.append(b("低成本：采用轻量模型与开源技术栈，单题诊断成本低至分币级。"))

story.append(p("4.3 典型使用场景", h2))
story.append(p(
    "<b>场景一（学生自学）</b>：小明做完家庭作业，发现一道「35+27」算成了 52。他拍照录入错题，"
    "自评「我觉得是算错了」，点击诊断后 AI 判定为「计算错误：个位相加未进位」，并给出分步解析。"
    "小明随后点「做一道同类题巩固」，当场再练一道 42+19，答对后系统将错题纳入遗忘曲线复习计划。"))
story.append(p(
    "<b>场景二（家长辅导）</b>：小明的妈妈打开「家长周报」，看到本周错题比上周少了 3 道，"
    "AI 提示「孩子近期在分数计算上反复出错，建议每天安排 10 分钟针对性练习」，妈妈据此针对性辅导。"))
story.append(p(
    "<b>场景三（教师教研）</b>：老师收集班级错题数据后，通过错因分布发现「审题错误」占比显著上升，"
    "从而在课堂上增加读题训练，实现数据驱动的教学改进。"))

# ================= 五、目标用户与功能需求 =================
story.append(p("五、目标用户群体与功能需求", h1))
story.append(p("5.1 目标用户群体", h2))
story.append(p(
    "<b>小学生（主要使用者）</b>：录入并复习自己的错题，通过 AI 诊断与多轮追问真正弄懂错因，养成自我觉察的元认知习惯。"
    "<b>家长（监督与陪伴者）</b>：通过学习报告与家长周报了解孩子的薄弱知识点与进步轨迹，获得可执行的辅导建议。"
    "<b>教师/教培机构（潜在用户）</b>：批量分析班级错题分布与高频错因，辅助针对性教学与教研。"))
story.append(p("5.2 核心功能需求一览", h2))
story.append(table(
    [
        ["功能模块", "功能说明", "AI 能力"],
        ["拍照识题", "上传题目图片，自动识别题干文字", "多模态视觉模型"],
        ["错因诊断", "判断错因类型与具体错点，给出正确步骤与建议", "大语言模型"],
        ["元认知校准", "学生自评错因与 AI 诊断对照，训练自我觉察", "大语言模型"],
        ["同类题巩固", "生成同类型题目并独立验算答案", "大语言模型 + 符号引擎"],
        ["遗忘曲线复习", "按 SM-2 算法安排复习时机", "—（算法）"],
        ["AI 多轮讲解", "就错题与 AI 老师持续追问，直到弄懂", "大语言模型（流式）"],
        ["学情报告", "错因分布、薄弱知识点、错误习惯画像", "大语言模型"],
        ["家长周报", "生成家长可读的周学习总结与建议", "大语言模型"],
    ],
    widths=[3.2 * cm, 8.6 * cm, 4.4 * cm],
))

# ================= 六、开发工具 =================
story.append(p("六、开发工具与环境", h1))
story.append(table(
    [
        ["类别", "工具/技术", "用途"],
        ["编程语言", "Python 3", "后端逻辑、AI 调度、数学校验"],
        ["前端框架", "Streamlit", "快速构建响应式 Web 界面"],
        ["数据库", "SQLite", "本地化错题数据存储，按用户隔离"],
        ["大模型", "智谱 GLM（glm-4-flash / glm-4v-flash）", "错因诊断、视觉识别、讲解生成"],
        ["模型接入", "OpenAI SDK（兼容协议）", "统一调用大模型 API"],
        ["符号计算", "sympy / Python ast", "确定性答案校验、方程求解"],
        ["文档生成", "reportlab", "生成 PDF 交付物"],
        ["版本管理", "Git", "代码版本控制"],
    ],
    widths=[3.0 * cm, 8.0 * cm, 5.2 * cm],
))

# ================= 七、技术方案 =================
story.append(p("七、技术方案", h1))
story.append(p("7.1 系统总体架构", h2))
story.append(p(
    "系统采用「前端展示层 — 业务逻辑层 — 数据与模型层」三层结构。前端由 Streamlit 提供响应式界面，"
    "业务逻辑层封装诊断、校验、复习调度等核心能力，数据层使用 SQLite 存储错题并按 user_id 隔离，"
    "模型层通过 OpenAI 兼容协议调用智谱 GLM 大模型。系统无需独立后端服务器，部署轻量、启动即用，"
    "支持桌面与移动端（含 PWA 安装）。"))
story.append(p(
    "系统核心数据流如下：用户通过界面录入错题 → 视觉模型识别题干（可选）→ 大模型诊断错因 → 符号引擎校验同类题答案 → "
    "结构化结果写入 SQLite → SM-2 算法调度复习时机 → 每日按计划推送复习 → 学习数据聚合生成报告。"
    "其中，AI 诊断与确定性校验构成「双引擎」——AI 负责生成与理解，符号引擎负责验证与兜底，二者相互独立、互为补充。"))
story.append(table(
    [
        ["层次", "组件", "职责"],
        ["展示层", "Streamlit 界面", "响应式交互、卡片化布局、流式输出"],
        ["业务层", "core.py（诊断/校验/生成/讲解）", "AI 调度、符号校验、结果归一化"],
        ["业务层", "review.py（SM-2）", "遗忘曲线复习调度"],
        ["数据层", "db.py（SQLite）", "错题存储、user_id 隔离、学情统计"],
        ["模型层", "智谱 GLM API", "文本诊断、视觉识别、讲解生成"],
    ],
    widths=[2.6 * cm, 6.4 * cm, 7.2 * cm],
))

story.append(p("7.2 核心 AI 技术方案（本作品创新重点）", h2))

story.append(p("① 可解释错因诊断（文本 + 多模态）", h2))
story.append(p(
    "诊断模块将「题目 + 学生错误答案」输入大模型，结合内置的小学数学知识分类体系（六大一级领域、四十余个二级题型），"
    "输出结构化诊断结果：错因分类（概念错误/计算错误/审题错误/方法错误）、具体错点、正确答案、分步解析与纠正建议。"
    "针对含几何图形的题目，系统自动切换至多模态视觉模型，将原图与文字一并输入，"
    "使模型能够直接读取图形中的阴影、角度、辅助线等关键信息，避免仅凭文字转述导致的信息丢失。"
    "诊断结果经过枚举归一化，确保分类与知识体系严格对齐。"))

story.append(p("② 确定性答案校验（不依赖 LLM 自检）", h2))
story.append(p(
    "针对「AI 会答错」这一行业通病，本作品引入独立的符号计算引擎对 AI 生成的答案进行客观校验："
    "使用 Python ast 模块以白名单方式安全解析四则运算表达式（仅允许数字与 + - * / 括号），"
    "以分数运算保证小数、分数计算的精确性；使用 sympy 求解一元方程，并对表达式做字符白名单校验以防止注入。"
    "该校验完全脱离大模型，确保答案客观可信——这是区别于作业帮、小猿搜题等「直接信任模型输出」方案的关键技术差异。"))

story.append(p("③ 元认知错因校准（授人以渔）", h2))
story.append(p(
    "基于教育心理学中的元认知理论，录入错题时先让学生自评「我觉得我错在哪儿」（概念没弄懂/算错了/没读懂题/不会方法），"
    "系统将自评结果与 AI 诊断结论对照，量化学生的「自我觉察准确率」，并在学习报告中绘制成长曲线。"
    "该设计将学生从「被动接受答案」转变为「自己错题的诊断者」，通过持续的对照反馈训练元认知能力，从根源上减少重复犯错。"))

story.append(p("④ 同类题生成即验证（可信闭环）", h2))
story.append(p(
    "生成同类题时，先由大模型出题并附带计算式，再由符号引擎独立验算答案；"
    "验算不通过则将错误反馈给模型并自动重试（最多三次），最终返回带「已验算/未验算」标记的题目。"
    "由此形成「生成 → 验证 → 修正」的可信闭环，保证推送给学生的题目答案准确可靠。"))

story.append(p("7.3 遗忘曲线复习调度", h2))
story.append(p(
    "采用经典 SM-2 间隔重复算法，根据每次复习的回忆质量（0~5）动态调整复习间隔与难度系数："
    "答对则延长间隔、答错或遗忘则重置并加强巩固，实现「该复习时才出现、不该复习不打扰」的科学复习节奏。"))

story.append(p("7.4 数据存储与安全", h2))
story.append(p(
    "使用 SQLite 单文件数据库，错题表以 user_id 字段实现多用户数据隔离，删除、更新操作均带用户校验，"
    "避免跨用户数据越权。用户数据本地化存储，无需上传第三方服务器，有效保障数据隐私。"))

story.append(p("7.5 关键技术难点与解决方案", h2))
story.append(table(
    [
        ["技术难点", "解决方案"],
        ["AI 生成答案不可信", "符号计算引擎独立验算，白名单解析 + 分数精确运算 + 方程求解"],
        ["几何图形信息易丢失", "诊断阶段切换多模态视觉模型，直接读取原图"],
        ["AI 分类用词不规范", "枚举归一化，将模型输出对齐到知识体系"],
        ["小数/分数比较不精确", "Fraction 分数运算，避免浮点误差"],
        ["符号求值存在注入风险", "ast 白名单节点 + sympy 字符白名单双重校验"],
        ["多用户数据混淆", "user_id 字段隔离，增删改均带用户校验"],
    ],
    widths=[5.6 * cm, 10.6 * cm],
))

# ================= 八、作品功能 =================
story.append(p("八、作品功能说明", h1))
story.append(p("本作品围绕「录题 → 诊断 → 复习 → 巩固 → 反馈」的学习闭环，提供八大功能。AI 能力贯穿始终，是产品的核心引擎。", body))

story.append(p("功能 1：拍照识题", h2))
story.append(p("学生上传题目照片，多模态视觉模型自动识别并提取题干文字，免去手打。识别结果可直接用于诊断；原图在诊断时同步传入，兼顾文字与图形信息，支持含几何图形的题目。"))

story.append(p("功能 2：AI 错因诊断（核心）", h2))
story.append(p("输入题目与学生错误答案后，AI 快速给出：错因分类、具体错点、正确答案、分步解析与一句话纠正建议。"
               "诊断拒绝「粗心」等空泛表述，指向具体可行动的改进点（如「进位时忘记加 1」），并自动将题目归入知识分类体系，为后续复习与报告奠定基础。"))
story.append(p("【解决痛点】直接回应「只抄答案、不理解错因」与「错因无法精准定位」两大痛点，"
               "把抽象的「做错了」转化为可理解、可执行的「错在哪、怎么改」。"))
story.append(p("【技术要点】以知识分类体系为约束，引导模型输出结构化 JSON；对模型返回的分类词做枚举归一化，"
               "确保与知识体系严格对齐；含图形时自动切换多模态视觉模型读取原图。"))

story.append(p("功能 3：元认知错因校准（核心创新）", h2))
story.append(p("诊断前让学生先判断自己错在哪（概念没弄懂/算错了/没读懂题/不会方法），诊断后对照展示「你的判断 vs AI 判断」。"
               "长期追踪「自我觉察准确率」并绘制成长曲线，帮助学生逐步建立对自身错误的清醒认知。"))
story.append(p("【解决痛点】针对「被动接受答案」的深层问题——搜题软件只告诉孩子「答案是什么」，"
               "本功能引导孩子思考「我为什么会错」，通过持续对照训练元认知能力，从根源上减少同类错误反复出现。"))
story.append(p("【技术要点】学生自评与 AI 诊断的四类错因做结构化映射，校准结果写入数据库，"
               "按时间维度聚合计算觉察准确率，并在学习报告中可视化成长曲线。"))

story.append(p("功能 4：同类题生成即验证（核心创新）", h2))
story.append(p("针对薄弱知识点一键生成同难度同类题，且每道题的答案都经过独立符号引擎验算，验证失败自动将错误反馈给模型重试。"
               "学生「当场练、当场验」，实现从「看懂了」到「真会了」的跨越。"))
story.append(p("【解决痛点】针对竞品「举一反三质量差、答案不可信」的短板——本功能保证推送给学生的题目答案客观正确，"
               "让学生练得放心，真正巩固薄弱点。"))
story.append(p("【技术要点】大模型出题并附带计算式，符号引擎以 ast 白名单 + 分数运算独立验算；"
               "验算不通过则将错误回传模型重试（最多三次），形成「生成—验证—修正」闭环。"))

story.append(p("功能 5：遗忘曲线复习", h2))
story.append(p("系统依据 SM-2 算法，每天自动列出「今日待复习」的错题。学生作答后，答对则延长复习间隔，答错或「还是不会」则缩短间隔、加强巩固，让复习节奏科学、高效。"))

story.append(p("功能 6：AI 多轮讲解", h2))
story.append(p("诊断后支持与「AI 老师」就错题持续追问（如「为什么这里要进位？」），采用流式输出逐字展示，引导式讲解、不直接甩答案，直到学生真正弄懂。"))

story.append(p("功能 7：学习报告与错误习惯画像", h2))
story.append(p("自动生成错因分布、薄弱知识点图表；并将高频具体错因归纳为可命名的「错误习惯」（如「进位漏 1 症」「不读单位症」），给出针对性的纠正方法，让抽象的学习问题变得可见、可改。"))

story.append(p("功能 8：家长周报", h2))
story.append(p("自动对比本周/上周错题数量，结合薄弱点生成家长可读的周报：一句话总结、最需关注的问题与可执行建议，让家长轻松掌握孩子的学习动态，实现家校共育。"))

# ================= 九、创新点总结 =================
story.append(p("九、核心创新点总结", h1))
story.append(b("<b>确定性答案校验</b>：以符号计算引擎独立验算 AI 生成答案，从根本上解决「AI 乱答」的行业痛点，是产品可信度的基石。"))
story.append(b("<b>元认知错因校准</b>：将学生自评与 AI 诊断对照，训练「自我觉察」能力，从「给答案」升级为「教方法」，是教育理念层面的差异化创新。"))
story.append(b("<b>多模态几何诊断</b>：诊断阶段直接读取题目原图，支持含图形的几何题，突破纯文字诊断的局限。"))
story.append(b("<b>生成即验证闭环</b>：将符号校验嵌入生成流程，实现「生成—验证—修正」的自动化闭环，保证推送题目质量。"))

# ================= 十、使用说明 =================
story.append(p("十、使用说明", h1))
story.append(p("10.1 快速开始", h2))
story.append(b("运行：在项目目录执行 streamlit run app.py，浏览器访问 http://localhost:8501。"))
story.append(b("进入：首次打开输入学生姓名，即可拥有独立的错题本（不同姓名数据互相隔离）。"))
story.append(b("移动端：手机浏览器打开地址后，选择「添加到主屏幕」，即可像 App 一样安装使用（PWA）。"))

story.append(p("10.2 用户操作流程", h2))
story.append(b("录入错题：上传题目图片（或手输）→ 填写错误答案 → 自评错因 → 点击「AI 诊断」。"))
story.append(b("诊断与追问：查看错因/题型/正确答案/步骤 → 可继续追问 AI 老师 → 可一键「做一道同类题巩固」。"))
story.append(b("存入错题本：确认弄懂后点击「存入错题本」，系统自动归类并纳入复习计划。"))
story.append(b("今日复习：每日查看待复习错题，作答或标记「还是不会」，系统自动更新复习计划。"))
story.append(b("我的错题本：按分类浏览、筛选、重做或删除错题。"))
story.append(b("学习报告 / 家长周报：随时查看错因分布、觉察度曲线、错误习惯画像与周总结。"))

story.append(p("10.3 交互指南", h2))
story.append(b("顶部数据卡片展示「累计错题 / 今日待复习 / 已掌握」，学习进度一目了然。"))
story.append(b("所有 AI 生成内容均以流式或进度提示反馈，等待过程有明确感知。"))
story.append(b("答对时给予正向鼓励，答错时提示「再想想」，避免直接打击积极性。"))
story.append(b("界面采用卡片化布局与活泼配色，关键按钮使用主色渐变突出，适配小学生认知习惯。"))

# ================= 十一、应用前景与商业模式 =================
story.append(p("十一、应用前景与商业模式", h1))
story.append(p("11.1 应用前景", h2))
story.append(p(
    "「双减」之后，家庭教育场景的智能辅导需求持续增长。小学数学作为最大基数的学段，错题诊断与个性化复习是刚性需求。"
    "本作品以「AI 错因诊断 + 确定性校验 + 元认知训练」形成差异化壁垒，"
    "既可独立作为 C 端产品服务家庭用户，也可作为能力组件嵌入教培机构、智能学习硬件、家校平台等场景，市场空间广阔。"))
story.append(p("11.2 商业模式", h2))
story.append(b("B2C 订阅制：面向家庭提供基础免费 + 会员增值（无限诊断、家长报告、多设备同步）。"))
story.append(b("B2B 服务：为教培机构、智能硬件厂商提供错题诊断与学情分析 API/组件授权。"))
story.append(b("数据洞察（合规前提）：脱敏后的错因分布与学情画像，可为教研、教辅出版提供参考。"))
story.append(p(
    "本作品坚持轻量化、低成本的技术路线，采用轻量大模型与开源技术栈，单题诊断成本低至分币级，"
    "具备规模化落地与商业化推广的可行性。"))

story.append(p("11.3 竞争壁垒", h2))
story.append(b("<b>技术壁垒</b>：确定性符号校验与多模态诊断的组合，需要「大模型 + 符号计算 + 教育知识体系」的深度融合，非简单套壳可复制。"))
story.append(b("<b>数据壁垒</b>：持续积累的错因标注数据与错误习惯画像，可反哺诊断模型持续优化，形成数据飞轮。"))
story.append(b("<b>理念壁垒</b>：「授人以渔」的元认知训练理念，构建了与「给答案型」搜题软件的本质区隔，更契合素质教育的长期方向。"))

# ================= 结语 =================
story.append(Spacer(1, 0.5 * cm))
story.append(HRFlowable(width="100%", thickness=0.8, color=PRIMARY))
story.append(Spacer(1, 0.3 * cm))
story.append(p(
    "智学错题助手不止于「整理错题」，更致力于回答每个孩子和家长最关心的问题——错在哪、为什么错、如何不再错。"
    "通过 AI 错因诊断、确定性答案校验与元认知训练三大核心能力，让 AI 真正成为孩子身边的「私人数学老师」，"
    "让每一道错题都转化为成长的台阶。", body))

# ---- 生成 ----
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "智学错题助手-项目说明.pdf")
doc = SimpleDocTemplate(out, pagesize=A4,
                        leftMargin=PAGE_MARGIN, rightMargin=PAGE_MARGIN,
                        topMargin=2.0 * cm, bottomMargin=1.8 * cm,
                        title="智学错题助手 · 项目说明")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"已生成：{out}")
