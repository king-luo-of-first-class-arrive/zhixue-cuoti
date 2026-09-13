"""SQLite 存储：错题表。按 user_id 隔离，每个用户一个独立错题本。"""
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta

DB = "mistakes.db"


@contextmanager
def _conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db():
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS mistakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT '',
                question TEXT NOT NULL,
                student_answer TEXT NOT NULL,
                error_category TEXT,
                error_specific TEXT,
                knowledge_point TEXT,
                category TEXT,
                correct_answer TEXT,
                self_category TEXT,
                calibration INTEGER,
                created_at TEXT DEFAULT (date('now')),
                repetition INTEGER DEFAULT 0,
                interval INTEGER DEFAULT 0,
                ease REAL DEFAULT 2.5,
                next_review TEXT DEFAULT (date('now'))
            )
            """
        )
        # 迁移：老库补后续新增列
        cols = [r[1] for r in c.execute("PRAGMA table_info(mistakes)")]
        if "category" not in cols:
            c.execute("ALTER TABLE mistakes ADD COLUMN category TEXT")
            c.execute("UPDATE mistakes SET category='未分类' WHERE category IS NULL")
        if "self_category" not in cols:
            c.execute("ALTER TABLE mistakes ADD COLUMN self_category TEXT")
        if "calibration" not in cols:
            c.execute("ALTER TABLE mistakes ADD COLUMN calibration INTEGER")
        if "user_id" not in cols:
            c.execute("ALTER TABLE mistakes ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")
        c.execute("CREATE INDEX IF NOT EXISTS idx_user ON mistakes(user_id)")


def add_mistake(user_id, diag, question, student_answer, self_category=None, calibration=None):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO mistakes (user_id, question, student_answer, error_category, "
            "error_specific, knowledge_point, category, correct_answer, "
            "self_category, calibration) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (user_id, question, student_answer, diag.get("error_category"),
             diag.get("error_specific"), diag.get("knowledge_point"),
             diag.get("category"), diag.get("correct_answer"),
             self_category, calibration),
        )
        return cur.lastrowid


def due_today(user_id):
    with _conn() as c:
        return c.execute(
            "SELECT * FROM mistakes WHERE user_id=? AND next_review <= date('now') "
            "ORDER BY next_review",
            (user_id,),
        ).fetchall()


def update_review(user_id, mistake_id, repetition, interval, ease):
    next_review = (date.today() + timedelta(days=interval)).isoformat()
    with _conn() as c:
        c.execute(
            "UPDATE mistakes SET repetition=?, interval=?, ease=?, next_review=? "
            "WHERE id=? AND user_id=?",
            (repetition, interval, ease, next_review, mistake_id, user_id),
        )


def all_mistakes(user_id, category=None):
    with _conn() as c:
        if category:
            return c.execute(
                "SELECT * FROM mistakes WHERE user_id=? AND category=? ORDER BY id DESC",
                (user_id, category),
            ).fetchall()
        return c.execute(
            "SELECT * FROM mistakes WHERE user_id=? ORDER BY id DESC", (user_id,)
        ).fetchall()


def category_stats(user_id):
    with _conn() as c:
        return c.execute(
            "SELECT category, COUNT(*) AS n FROM mistakes WHERE user_id=? "
            "GROUP BY category ORDER BY n DESC",
            (user_id,),
        ).fetchall()


def delete_mistake(user_id, mistake_id):
    with _conn() as c:
        c.execute("DELETE FROM mistakes WHERE id=? AND user_id=?", (mistake_id, user_id))


def error_stats(user_id):
    with _conn() as c:
        return c.execute(
            "SELECT error_category, COUNT(*) AS n FROM mistakes WHERE user_id=? "
            "GROUP BY error_category ORDER BY n DESC",
            (user_id,),
        ).fetchall()


def knowledge_stats(user_id):
    with _conn() as c:
        return c.execute(
            "SELECT category, knowledge_point, COUNT(*) AS n FROM mistakes "
            "WHERE user_id=? GROUP BY category, knowledge_point ORDER BY n DESC",
            (user_id,),
        ).fetchall()


def weak_patterns(user_id, threshold=2):
    """同题型+同错因反复出现 >= threshold 次的模式，用于归因分析。"""
    with _conn() as c:
        return c.execute(
            "SELECT category, knowledge_point, error_category, COUNT(*) AS n "
            "FROM mistakes WHERE user_id=? "
            "GROUP BY category, knowledge_point, error_category "
            "HAVING n >= ? ORDER BY n DESC",
            (user_id, threshold),
        ).fetchall()


def count_since(user_id, days):
    """最近 days 天内的错题数。"""
    with _conn() as c:
        return c.execute(
            "SELECT COUNT(*) FROM mistakes WHERE user_id=? AND created_at >= date('now', ?)",
            (user_id, f"-{days} day"),
        ).fetchone()[0]


def count_between(user_id, start_days, end_days):
    """start_days 到 end_days 天前之间的错题数（start_days > end_days）。"""
    with _conn() as c:
        return c.execute(
            "SELECT COUNT(*) FROM mistakes WHERE user_id=? AND created_at >= date('now', ?) "
            "AND created_at < date('now', ?)",
            (user_id, f"-{start_days} day", f"-{end_days} day"),
        ).fetchone()[0]


def calibration_stats(user_id):
    """按天统计元认知觉察准确率（校准=1 的数量 / 自评总数）。"""
    with _conn() as c:
        return c.execute(
            "SELECT created_at AS d, "
            "SUM(CASE WHEN calibration = 1 THEN 1 ELSE 0 END) AS ok, "
            "SUM(CASE WHEN calibration IS NOT NULL THEN 1 ELSE 0 END) AS total "
            "FROM mistakes WHERE user_id=? AND calibration IS NOT NULL "
            "GROUP BY created_at ORDER BY created_at",
            (user_id,),
        ).fetchall()


def specific_error_stats(user_id, limit=20):
    """按具体错因（error_specific）聚合，供错误习惯画像使用。"""
    with _conn() as c:
        return c.execute(
            "SELECT error_specific, COUNT(*) AS n FROM mistakes "
            "WHERE user_id=? AND error_specific IS NOT NULL AND error_specific != '' "
            "GROUP BY error_specific ORDER BY n DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()


def overview_stats(user_id):
    """首页激励栏统计：累计错题、今日待复习、已掌握（复习>=3次）。"""
    with _conn() as c:
        total = c.execute(
            "SELECT COUNT(*) FROM mistakes WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        due = c.execute(
            "SELECT COUNT(*) FROM mistakes WHERE user_id=? AND next_review <= date('now')",
            (user_id,),
        ).fetchone()[0]
        mastered = c.execute(
            "SELECT COUNT(*) FROM mistakes WHERE user_id=? AND repetition >= 3",
            (user_id,),
        ).fetchone()[0]
    return {"total": total, "due": due, "mastered": mastered}
