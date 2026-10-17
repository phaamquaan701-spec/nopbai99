import sqlite3
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo
from app.config import DB_PATH, DEFAULT_TIMEZONE

def get_current_iso_time():
    return datetime.now(DEFAULT_TIMEZONE).isoformat()

def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

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

def init_db():
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
        
    print("Database initialized with proper tables and indexes.")

if __name__ == "__main__":
    init_db()
