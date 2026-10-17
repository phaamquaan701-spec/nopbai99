"""
database.py — Hỗ trợ cả PostgreSQL (Neon/Vercel) và SQLite (local).

Cách hoạt động:
  - Nếu biến môi trường DATABASE_URL được set (trên Vercel/Neon) → dùng PostgreSQL.
  - Nếu không → dùng SQLite như cũ (phát triển local).

Lưu ý PostgreSQL vs SQLite:
  - Placeholder: PostgreSQL dùng %s thay vì ? của SQLite.
  - AUTOINCREMENT → SERIAL (PostgreSQL tự động).
  - INTEGER PRIMARY KEY AUTOINCREMENT → SERIAL PRIMARY KEY.
  - Không có PRAGMA.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo
from app.config import DB_PATH, DEFAULT_TIMEZONE

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# PostgreSQL hay SQLite?
USE_POSTGRES = bool(DATABASE_URL)

def get_current_iso_time():
    return datetime.now(DEFAULT_TIMEZONE).isoformat()


# ─────────────────────────────────────────────
# SQLite helpers (local dev)
# ─────────────────────────────────────────────

def _get_sqlite_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


# ─────────────────────────────────────────────
# PostgreSQL helpers (Neon / Vercel)
# ─────────────────────────────────────────────

class _PgRowProxy(dict):
    """Giả lập sqlite3.Row — truy cập bằng tên cột hoặc index."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class _PgCursor:
    """Wrapper cursor PostgreSQL — tự động đổi ? → %s và trả về dict-row."""
    def __init__(self, cursor):
        self._cur = cursor
        self.lastrowid = None
        self.rowcount = 0

    def _convert(self, sql: str) -> str:
        return sql.replace("?", "%s")

    def execute(self, sql: str, params=None):
        sql = self._convert(sql)
        # Đổi COLLATE NOCASE thành không có gì (PostgreSQL dùng ILIKE thay thế)
        sql = sql.replace("COLLATE NOCASE", "")
        
        sql_stripped = sql.strip().rstrip(";")
        # Nếu là câu lệnh INSERT, tự động gắn RETURNING id để lấy cursor.lastrowid
        if sql_stripped.lower().startswith("insert into") and "returning" not in sql_stripped.lower():
            sql = sql_stripped + " RETURNING id;"
            if params:
                self._cur.execute(sql, params)
            else:
                self._cur.execute(sql)
            try:
                row = self._cur.fetchone()
                if row:
                    self.lastrowid = row[0]
            except Exception:
                pass
            self.rowcount = self._cur.rowcount
            return self

        if params:
            self._cur.execute(sql, params)
        else:
            self._cur.execute(sql)
        self.rowcount = self._cur.rowcount
        return self

    def fetchone(self):
        if not self._cur.description:
            return None
        row = self._cur.fetchone()
        if row is None:
            return None
        cols = [desc[0] for desc in self._cur.description]
        return _PgRowProxy(zip(cols, row))

    def fetchall(self):
        if not self._cur.description:
            return []
        rows = self._cur.fetchall()
        if not rows:
            return []
        cols = [desc[0] for desc in self._cur.description]
        return [_PgRowProxy(zip(cols, r)) for r in rows]

    @property
    def description(self):
        return self._cur.description


class _PgConnection:
    """Wrapper connection PostgreSQL — giả lập interface sqlite3.Connection."""
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        return _PgCursor(self._conn.cursor())

    def execute(self, sql: str, params=None):
        cur = _PgCursor(self._conn.cursor())
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _get_pg_connection():
    import psycopg2
    # Neon yêu cầu sslmode=require, hỗ trợ cả postgres:// và postgresql://
    url = DATABASE_URL.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if "sslmode" not in url:
        url = url + ("&" if "?" in url else "?") + "sslmode=require"
    raw = psycopg2.connect(url)
    return _PgConnection(raw)


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def get_db_connection():
    if USE_POSTGRES:
        return _get_pg_connection()
    return _get_sqlite_connection()


@contextmanager
def get_db():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─────────────────────────────────────────────
# Schema khởi tạo
# ─────────────────────────────────────────────

def init_db():
    if USE_POSTGRES:
        _init_pg()
    else:
        _init_sqlite()
    print("Database initialized.")


def _init_sqlite():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'student')),
            class_id INTEGER NULL REFERENCES classes(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'locked')),
            created_at TEXT NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            subject TEXT NOT NULL,
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            created_by INTEGER NOT NULL REFERENCES users(id),
            start_at TEXT NOT NULL,
            deadline TEXT NOT NULL,
            allow_resubmit INTEGER NOT NULL DEFAULT 1,
            allow_late_submission INTEGER NOT NULL DEFAULT 0,
            resubmit_after_deadline INTEGER NOT NULL DEFAULT 0,
            submission_grace_period INTEGER NOT NULL DEFAULT 300,
            max_images INTEGER NOT NULL DEFAULT 10,
            max_file_size INTEGER NOT NULL DEFAULT 10485760,
            status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'closed')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
            student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            submitted_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'submitted',
            attempt_number INTEGER NOT NULL DEFAULT 1,
            is_late INTEGER NOT NULL DEFAULT 0,
            late_seconds INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS submission_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
            storage_key TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            sanitized_filename TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_class_id ON users(class_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_class_id ON assignments(class_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_assignments_deadline ON assignments(deadline);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_submissions_assign_student ON submissions(assignment_id, student_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_submission_files_sub ON submission_files(submission_id);")


def _init_pg():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'student')),
            class_id INTEGER NULL REFERENCES classes(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'locked')),
            created_at TEXT NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            subject TEXT NOT NULL,
            class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
            created_by INTEGER NOT NULL REFERENCES users(id),
            start_at TEXT NOT NULL,
            deadline TEXT NOT NULL,
            allow_resubmit INTEGER NOT NULL DEFAULT 1,
            allow_late_submission INTEGER NOT NULL DEFAULT 0,
            resubmit_after_deadline INTEGER NOT NULL DEFAULT 0,
            submission_grace_period INTEGER NOT NULL DEFAULT 300,
            max_images INTEGER NOT NULL DEFAULT 10,
            max_file_size INTEGER NOT NULL DEFAULT 10485760,
            status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'closed')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id SERIAL PRIMARY KEY,
            assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
            student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            submitted_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'submitted',
            attempt_number INTEGER NOT NULL DEFAULT 1,
            is_late INTEGER NOT NULL DEFAULT 0,
            late_seconds INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS submission_files (
            id SERIAL PRIMARY KEY,
            submission_id INTEGER NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
            storage_key TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            sanitized_filename TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """)
        # Indexes (PostgreSQL dùng IF NOT EXISTS từ v9.5+)
        for ddl in [
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
            "CREATE INDEX IF NOT EXISTS idx_users_class_id ON users(class_id);",
            "CREATE INDEX IF NOT EXISTS idx_assignments_class_id ON assignments(class_id);",
            "CREATE INDEX IF NOT EXISTS idx_assignments_deadline ON assignments(deadline);",
            "CREATE INDEX IF NOT EXISTS idx_submissions_assign_student ON submissions(assignment_id, student_id);",
            "CREATE INDEX IF NOT EXISTS idx_submission_files_sub ON submission_files(submission_id);",
        ]:
            cursor.execute(ddl)


if __name__ == "__main__":
    init_db()
