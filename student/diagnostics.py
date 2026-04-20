# new-agent/student/diagnostics.py
"""Learning diagnostics — analyze student memory to identify weak points."""

from __future__ import annotations

from chat.prompts import DIAGNOSTICS_SYSTEM
from llm.client import ChatClient
from student.memory import StudentMemory


class LearningDiagnostics:
    """Analyzes student learning data and produces a diagnosis."""

    def __init__(self, llm: ChatClient):
        self.llm = llm

    def analyze(self, memory: StudentMemory) -> dict:
        """Statistical analysis of student performance.

        Returns a structured diagnosis without LLM.
        """
        topics = memory.get_topics()
        weak = memory.get_weak_points()
        strong = memory.get_strong_points()
        errors = memory.get_errors()
        quizzes = memory.get_quiz_scores()

        # Compute overall accuracy
        total_correct = sum(t["correct"] for t in topics.values())
        total_wrong = sum(t["wrong"] for t in topics.values())
        total = total_correct + total_wrong
        accuracy = total_correct / total if total > 0 else 0

        # Quiz average
        quiz_avg = 0
        if quizzes:
            valid_quizzes = [q for q in quizzes if q["total"] > 0]
            if valid_quizzes:
                quiz_avg = sum(q["score"] / q["total"] for q in valid_quizzes) / len(valid_quizzes)

        # Determine overall level
        if accuracy >= 0.85 and quiz_avg >= 0.85:
            level = "优秀"
        elif accuracy >= 0.7 and quiz_avg >= 0.7:
            level = "良好"
        elif accuracy >= 0.5:
            level = "一般"
        else:
            level = "薄弱"

        # Recent error patterns
        recent_errors = errors[-10:]
        error_topics = {}
        for e in recent_errors:
            t = e["topic"]
            error_topics[t] = error_topics.get(t, 0) + 1

        return {
            "level": level,
            "accuracy": round(accuracy, 2),
            "quiz_average": round(quiz_avg, 2),
            "total_interactions": total,
            "weak_points": weak,
            "strong_points": strong,
            "error_distribution": error_topics,
            "recent_errors": recent_errors,
            "suggestions": self._generate_suggestions(weak, strong, accuracy),
        }

    async def diagnose(self, memory: StudentMemory) -> str:
        """LLM-powered diagnosis with natural language explanation."""
        summary = memory.get_summary()
        errors = memory.get_errors(10)
        quizzes = memory.get_quiz_scores(5)

        records_text = f"""知识点掌握情况：
{self._format_topics(summary['topics'])}

近期错误记录：
{self._format_errors(errors)}

近期测验成绩：
{self._format_quizzes(quizzes)}"""

        prompt = DIAGNOSTICS_SYSTEM.format(learning_records=records_text)
        return await self.llm.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
        )

    def _format_topics(self, topics: dict) -> str:
        if not topics:
            return "暂无记录"
        lines = []
        for name, stats in topics.items():
            total = stats["correct"] + stats["wrong"]
            rate = stats["correct"] / total if total > 0 else 0
            bar = "█" * int(rate * 10) + "░" * (10 - int(rate * 10))
            lines.append(f"  {name}: {bar} {rate:.0%} (对{stats['correct']}/错{stats['wrong']})")
        return "\n".join(lines)

    def _format_errors(self, errors: list[dict]) -> str:
        if not errors:
            return "暂无错误记录"
        lines = []
        for e in errors:
            lines.append(f"  [{e['topic']}] 题目: {e['question'][:50]}... | 学生: {e['student_answer'][:30]} | 正确: {e['correct_answer'][:30]}")
        return "\n".join(lines)

    def _format_quizzes(self, quizzes: list[dict]) -> str:
        if not quizzes:
            return "暂无测验记录"
        lines = []
        for q in quizzes:
            lines.append(f"  [{q['topic']}] {q['score']}/{q['total']} ({q['date'][:10]})")
        return "\n".join(lines)

    def _generate_suggestions(self, weak: list[str], strong: list[str], accuracy: float) -> list[str]:
        suggestions = []
        if weak:
            suggestions.append(f"重点复习: {', '.join(weak)}")
        if accuracy < 0.5:
            suggestions.append("建议从基础概念重新学习")
        elif accuracy < 0.7:
            suggestions.append("加强练习，特别是薄弱知识点")
        if strong:
            suggestions.append(f"已掌握较好的知识点: {', '.join(strong)}，可以作为信心基础")
        return suggestions
