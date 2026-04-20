# new-agent/student/memory.py
"""Per-student, per-subject memory files — learning profile persistence."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from config import STUDENTS_DIR


class StudentMemory:
    """Manages a student's learning memory for a specific subject.

    Stored as a JSON file at: data/students/{student_id}/{subject}_memory.json
    """

    def __init__(self, student_id: str, subject: str):
        self.student_id = student_id
        self.subject = subject
        self.dir = STUDENTS_DIR / student_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f"{subject}_memory.json"
        self._data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Corrupt file — start fresh
                return self._default_data()
        return self._default_data()

    def _default_data(self) -> dict:
        return {
            "student_id": self.student_id,
            "subject": self.subject,
            "created_at": datetime.now().isoformat(),
            "topics": {},          # topic_name -> {"correct": int, "wrong": int, "last_seen": str}
            "errors": [],          # list of error records
            "quiz_scores": [],     # list of {topic, score, total, date}
            "question_log": [],    # recent questions asked
            "weak_points": [],     # identified weak topics
            "strong_points": [],   # identified strong topics
        }

    def save(self) -> None:
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # --- Topic tracking ---

    def record_topic(self, topic: str, correct: bool) -> None:
        """Record an interaction on a topic (question answered correctly or not)."""
        if topic not in self._data["topics"]:
            self._data["topics"][topic] = {"correct": 0, "wrong": 0, "last_seen": ""}
        entry = self._data["topics"][topic]
        if correct:
            entry["correct"] += 1
        else:
            entry["wrong"] += 1
        entry["last_seen"] = datetime.now().isoformat()
        self.save()

    def record_error(self, topic: str, question: str, student_answer: str, correct_answer: str) -> None:
        """Record a specific error for diagnostics."""
        self._data["errors"].append({
            "topic": topic,
            "question": question,
            "student_answer": student_answer,
            "correct_answer": correct_answer,
            "date": datetime.now().isoformat(),
        })
        # Keep only last 50 errors
        self._data["errors"] = self._data["errors"][-50:]
        self.save()

    def record_quiz(self, topic: str, score: int, total: int) -> None:
        """Record a quiz result."""
        if total <= 0:
            return
        self._data["quiz_scores"].append({
            "topic": topic,
            "score": score,
            "total": total,
            "date": datetime.now().isoformat(),
        })
        self._data["quiz_scores"] = self._data["quiz_scores"][-30:]
        self.save()

    def log_question(self, question: str, topic: str = "") -> None:
        """Log a question asked by the student."""
        self._data["question_log"].append({
            "question": question,
            "topic": topic,
            "date": datetime.now().isoformat(),
        })
        self._data["question_log"] = self._data["question_log"][-100:]
        self.save()

    # --- Query helpers ---

    def get_topics(self) -> dict:
        return self._data["topics"]

    def get_errors(self, limit: int = 20) -> list[dict]:
        return self._data["errors"][-limit:]

    def get_quiz_scores(self, limit: int = 10) -> list[dict]:
        return self._data["quiz_scores"][-limit:]

    def get_weak_points(self) -> list[str]:
        """Return topics where the error rate is above 40%."""
        weak = []
        for topic, stats in self._data["topics"].items():
            total = stats["correct"] + stats["wrong"]
            if total >= 2 and stats["wrong"] / total > 0.4:
                weak.append(topic)
        self._data["weak_points"] = weak
        return weak

    def get_strong_points(self) -> list[str]:
        """Return topics where the correct rate is above 80%."""
        strong = []
        for topic, stats in self._data["topics"].items():
            total = stats["correct"] + stats["wrong"]
            if total >= 2 and stats["correct"] / total > 0.8:
                strong.append(topic)
        self._data["strong_points"] = strong
        return strong

    def get_summary(self) -> dict:
        """Get a compact summary of the student's profile."""
        return {
            "student_id": self.student_id,
            "subject": self.subject,
            "total_topics": len(self._data["topics"]),
            "total_errors": len(self._data["errors"]),
            "total_quizzes": len(self._data["quiz_scores"]),
            "weak_points": self.get_weak_points(),
            "strong_points": self.get_strong_points(),
            "topics": self._data["topics"],
        }
