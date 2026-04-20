# new-agent/exercise/evaluator.py
"""Exercise evaluation — grade student answers and provide feedback."""

from __future__ import annotations

from chat.prompts import EXERCISE_EVALUATION_SYSTEM
from llm.client import ChatClient
from student.memory import StudentMemory


class ExerciseEvaluator:
    """Evaluates student answers and records results."""

    def __init__(self, llm: ChatClient):
        self.llm = llm

    async def evaluate(
        self,
        question: str,
        correct_answer: str,
        student_answer: str,
        *,
        topic: str = "",
        memory: StudentMemory | None = None,
    ) -> str:
        """Evaluate a student's answer and return feedback.

        If memory is provided, records the result for diagnostics.
        """
        system = EXERCISE_EVALUATION_SYSTEM.format(
            question=question,
            correct_answer=correct_answer,
            student_answer=student_answer,
        )

        feedback = await self.llm.chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": "请对以上答案进行评价。"},
            ],
            temperature=0.3,
        )

        # Determine correctness (simple heuristic)
        is_correct = self.check_correct(correct_answer, student_answer)

        # Record to memory
        if memory and topic:
            memory.record_topic(topic, is_correct)
            if not is_correct:
                memory.record_error(topic, question, student_answer, correct_answer)

        return feedback

    async def evaluate_batch(
        self,
        questions: list[dict],
        student_answers: dict[int, str],
        *,
        topic: str = "",
        memory: StudentMemory | None = None,
    ) -> list[dict]:
        """Evaluate a batch of questions. Returns list of {question_id, correct, feedback}."""
        results = []
        correct_count = 0

        for q in questions:
            q_id = q.get("id", 0)
            q_text = q.get("question", "")
            correct = str(q.get("answer", ""))
            student = student_answers.get(q_id, "")

            feedback = await self.evaluate(
                q_text, correct, student,
                topic=topic, memory=memory,
            )

            is_correct = self.check_correct(correct, student)
            if is_correct:
                correct_count += 1

            results.append({
                "question_id": q_id,
                "correct": is_correct,
                "feedback": feedback,
            })

        # Record quiz score
        if memory and topic:
            memory.record_quiz(topic, correct_count, len(questions))

        return results

    def check_correct(self, correct: str, student: str) -> bool:
        """Simple correctness check."""
        correct = correct.strip().upper()
        student = student.strip().upper()
        # Direct match
        if correct == student:
            return True
        # For single-letter answers (A/B/C/D)
        if len(correct) == 1 and len(student) >= 1 and correct == student[0]:
            return True
        return False
