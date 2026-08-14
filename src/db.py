import sqlite3
import threading
from pathlib import Path
from typing import Optional
from src.models import Student, Assignment, Evaluation, Rubric, Grade


class Database:
    """SQLite database for storing evaluations, students, and rubrics.
    
    Thread-safe: uses per-thread connections with checkpointing.
    """

    _local = threading.local()

    def __init__(self, db_path: str = "data/evaluations.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._main_conn = sqlite3.connect(str(self.db_path))
        self._main_conn.execute("PRAGMA journal_mode=WAL")
        self._main_conn.row_factory = sqlite3.Row
        self._create_tables()
        self._main_conn.commit()

    def _get_conn(self):
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    @property
    def conn(self):
        """Thread-safe connection property."""
        return self._get_conn()

    @conn.setter
    def conn(self, value):
        self._main_conn = value

    def _create_tables(self):
        """Create database tables if they don't exist."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                cohort TEXT DEFAULT '2026-02',
                github_username TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                module TEXT NOT NULL,
                topic_key TEXT NOT NULL UNIQUE,
                num_exercises INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                weight REAL DEFAULT 1.0
            );

            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                assignment_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                grade TEXT NOT NULL,
                numeric_grade INTEGER NOT NULL,
                markdown_report TEXT NOT NULL,
                unresolved_exercises INTEGER DEFAULT 0,
                topic_key TEXT,
                override_reason TEXT,
                override_at TEXT,
                evaluated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (assignment_id) REFERENCES assignments(id)
            );

            CREATE TABLE IF NOT EXISTS exercise_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_id INTEGER NOT NULL,
                exercise_number INTEGER NOT NULL,
                exercise_name TEXT NOT NULL,
                issue TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                FOREIGN KEY (evaluation_id) REFERENCES evaluations(id)
            );

            CREATE TABLE IF NOT EXISTS rubrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_key TEXT NOT NULL UNIQUE,
                assignment_name TEXT NOT NULL,
                module TEXT NOT NULL,
                num_exercises INTEGER DEFAULT 0,
                content TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_evaluations_student
                ON evaluations(student_id);
            CREATE INDEX IF NOT EXISTS idx_evaluations_assignment
                ON evaluations(assignment_id);
            CREATE INDEX IF NOT EXISTS idx_evaluations_grade
                ON evaluations(grade);

            CREATE TABLE IF NOT EXISTS reference_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_key TEXT NOT NULL UNIQUE,
                total_exercises INTEGER NOT NULL,
                exercises_requiring_code INTEGER NOT NULL,
                exercises_json TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        self.conn.commit()

    # Student operations
    def add_student(self, student: Student) -> int:
        """Add a student and return their ID."""
        cursor = self.conn.execute(
            """INSERT INTO students (name, email, cohort, github_username)
               VALUES (?, ?, ?, ?)""",
            (student.name, student.email, student.cohort, student.github_username)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_student(self, name: str) -> Optional[dict]:
        """Get student by name."""
        row = self.conn.execute(
            "SELECT * FROM students WHERE name = ?", (name,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_students(self) -> list[dict]:
        """Get all students."""
        rows = self.conn.execute("SELECT * FROM students ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    # Assignment operations
    def add_assignment(self, assignment: Assignment) -> int:
        """Add an assignment and return its ID."""
        cursor = self.conn.execute(
            """INSERT OR REPLACE INTO assignments
               (name, module, topic_key, num_exercises, description, weight)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (assignment.name, assignment.module, assignment.topic_key,
             assignment.num_exercises, assignment.description, assignment.weight)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_assignment(self, topic_key: str) -> Optional[dict]:
        """Get assignment by topic key."""
        row = self.conn.execute(
            "SELECT * FROM assignments WHERE topic_key = ?", (topic_key,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_assignments(self) -> list[dict]:
        """Get all assignments."""
        rows = self.conn.execute(
            "SELECT * FROM assignments ORDER BY module, name"
        ).fetchall()
        return [dict(r) for r in rows]

    # Evaluation operations
    def add_evaluation(self, evaluation: Evaluation) -> int:
        """Add an evaluation and return its ID."""
        cursor = self.conn.execute(
            """INSERT INTO evaluations
               (student_id, assignment_id, filename, grade, numeric_grade,
                markdown_report, unresolved_exercises, topic_key, evaluated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (evaluation.student_id, evaluation.assignment_id, evaluation.filename,
             evaluation.grade.value, evaluation.numeric_grade,
             evaluation.markdown_report, evaluation.unresolved_exercises,
             evaluation.topic_key, evaluation.evaluated_at)
        )
        eval_id = cursor.lastrowid

        # Add exercise issues
        for issue in evaluation.exercise_issues:
            self.conn.execute(
                """INSERT INTO exercise_issues
                   (evaluation_id, exercise_number, exercise_name, issue, recommendation)
                   VALUES (?, ?, ?, ?, ?)""",
                (eval_id, issue.exercise_number, issue.exercise_name,
                 issue.issue, issue.recommendation)
            )

        self.conn.commit()
        return eval_id

    def get_evaluation(self, student_id: int, assignment_id: int) -> Optional[dict]:
        """Get evaluation for a student and assignment."""
        row = self.conn.execute(
            """SELECT * FROM evaluations
               WHERE student_id = ? AND assignment_id = ?
               ORDER BY evaluated_at DESC LIMIT 1""",
            (student_id, assignment_id)
        ).fetchone()
        return dict(row) if row else None

    def get_student_evaluations(self, student_id: int) -> list[dict]:
        """Get all evaluations for a student."""
        rows = self.conn.execute(
            """SELECT e.*, COALESCE(e.topic_key, a.topic_key) as topic_key, a.name as assignment_name, a.module
               FROM evaluations e
               JOIN assignments a ON e.assignment_id = a.id
               WHERE e.student_id = ?
               ORDER BY e.evaluated_at DESC""",
            (student_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_cohort_stats(self, assignment_id: int) -> dict:
        """Get cohort statistics for an assignment."""
        row = self.conn.execute(
            """SELECT
               COUNT(*) as total_evaluated,
               AVG(numeric_grade) as avg_grade,
               MIN(numeric_grade) as min_grade,
               MAX(numeric_grade) as max_grade,
               SUM(CASE WHEN grade = 'Excepcional' THEN 1 ELSE 0 END) as excepcionales,
               SUM(CASE WHEN grade = 'Bien' THEN 1 ELSE 0 END) as bienes,
               SUM(CASE WHEN grade = 'Regular' THEN 1 ELSE 0 END) as regulares,
               SUM(CASE WHEN grade = 'Mal' THEN 1 ELSE 0 END) as males
               FROM evaluations
               WHERE assignment_id = ?""",
            (assignment_id,)
        ).fetchone()
        return dict(row) if row else {}

    def get_all_evaluations(self) -> list[dict]:
        """Get all evaluations."""
        rows = self.conn.execute(
            """SELECT e.*, COALESCE(e.topic_key, a.topic_key) as topic_key, s.name as student_name, a.name as assignment_name
               FROM evaluations e
               JOIN students s ON e.student_id = s.id
               JOIN assignments a ON e.assignment_id = a.id
               ORDER BY e.evaluated_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]

    def update_evaluation_grade(self, eval_id: int, new_grade: str,
                                 reason: Optional[str] = None) -> bool:
        """Update evaluation grade with override reason."""
        from datetime import datetime
        grade_map = {"Mal": 3, "Regular": 5, "Bien": 7, "Excepcional": 9}
        numeric = grade_map.get(new_grade, 5)
        self.conn.execute(
            """UPDATE evaluations
               SET grade = ?, numeric_grade = ?,
                   override_reason = ?,
                   override_at = datetime('now')
               WHERE id = ?""",
            (new_grade, numeric, reason, eval_id)
        )
        self.conn.commit()
        return self.conn.rowsaffected > 0

    # Rubric operations
    def add_rubric(self, rubric: Rubric) -> int:
        """Add a rubric and return its ID."""
        cursor = self.conn.execute(
            """INSERT OR REPLACE INTO rubrics
               (topic_key, assignment_name, module, num_exercises, content, weight)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (rubric.topic_key, rubric.assignment_name, rubric.module,
             rubric.num_exercises, rubric.content, rubric.weight)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_rubric(self, topic_key: str) -> Optional[dict]:
        """Get rubric by topic key."""
        row = self.conn.execute(
            "SELECT * FROM rubrics WHERE topic_key = ?", (topic_key,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_rubrics(self) -> list[dict]:
        """Get all rubrics."""
        rows = self.conn.execute("SELECT * FROM rubrics ORDER BY module, assignment_name").fetchall()
        return [dict(r) for r in rows]

    # Reference metadata operations
    def add_reference_metadata(self, topic_key: str, total_exercises: int,
                                exercises_requiring_code: int,
                                exercises_json: str) -> int:
        """Add reference metadata for a task."""
        cursor = self.conn.execute(
            """INSERT OR REPLACE INTO reference_metadata
               (topic_key, total_exercises, exercises_requiring_code, exercises_json)
               VALUES (?, ?, ?, ?)""",
            (topic_key, total_exercises, exercises_requiring_code, exercises_json)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_reference_metadata(self, topic_key: str) -> Optional[dict]:
        """Get reference metadata for a task."""
        row = self.conn.execute(
            "SELECT * FROM reference_metadata WHERE topic_key = ?", (topic_key,)
        ).fetchone()
        return dict(row) if row else None

    def close(self):
        """Close database connections."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
        self._main_conn.close()
