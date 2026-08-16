from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class Grade(Enum):
    MAL = "Mal"
    REGULAR = "Regular"
    BIEN = "Bien"
    EXCEPCIONAL = "Excepcional"

    @property
    def numeric(self) -> int:
        return {"Mal": 3, "Regular": 5, "Bien": 7, "Excepcional": 9}[self.value]


@dataclass
class Student:
    name: str
    email: Optional[str] = None
    cohort: str = "2026-02"
    github_username: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Assignment:
    name: str
    module: str  # "NumPy I", "Pandas", etc.
    topic_key: str  # "numpy_i", "pandas_i", etc.
    num_exercises: int = 0
    description: str = ""
    weight: float = 1.0


@dataclass
class ExerciseIssue:
    exercise_number: int
    exercise_name: str
    issue: str
    recommendation: str


@dataclass
class Evaluation:
    student_id: int
    assignment_id: int
    filename: str
    grade: Grade
    numeric_grade: int
    markdown_report: str
    unresolved_exercises: int = 0
    exercise_issues: list = field(default_factory=list)
    topic_key: str = ""
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Rubric:
    topic_key: str
    assignment_name: str
    module: str
    num_exercises: int
    content: str  # Full rubric Markdown content
    weight: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
