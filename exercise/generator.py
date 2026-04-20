# new-agent/exercise/generator.py
"""Exercise generation — produces questions on demand."""

from __future__ import annotations

import json

from chat.prompts import EXERCISE_GENERATION_SYSTEM
from llm.client import ChatClient


class ExerciseGenerator:
    """Generates exercises using LLM with structured output."""

    def __init__(self, llm: ChatClient):
        self.llm = llm

    async def generate(
        self,
        topic: str,
        *,
        difficulty: str = "medium",
        question_type: str = "choice",
        count: int = 5,
        context: str = "",
    ) -> list[dict]:
        """Generate exercises on a given topic.

        Args:
            topic: The knowledge topic to test.
            difficulty: easy / medium / hard
            question_type: choice / fill / short_answer / coding
            count: Number of questions to generate.
            context: Optional additional context (e.g., from knowledge base).

        Returns:
            List of question dicts with id, type, difficulty, question, options, answer, explanation.
        """
        type_labels = {
            "choice": "选择题",
            "fill": "填空题",
            "short_answer": "简答题",
            "coding": "编程题",
        }
        type_label = type_labels.get(question_type, question_type)

        system = EXERCISE_GENERATION_SYSTEM.format(
            topic=topic,
            difficulty=difficulty,
            question_type=type_label,
            count=count,
        )

        if context:
            system = f"参考资料：\n{context}\n\n{system}"

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"请生成{count}道关于「{topic}」的{type_label}，难度：{difficulty}"},
        ]

        response = await self.llm.chat(messages, temperature=0.7)

        # Parse JSON from response
        questions = self._parse_json(response)
        return questions

    def _parse_json(self, text: str) -> list[dict]:
        """Extract JSON questions from LLM response."""
        # Try to find JSON block
        text = text.strip()
        # Remove markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(text)
            if isinstance(data, dict) and "questions" in data:
                return data["questions"]
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        # Fallback: try to find JSON object or array in text
        for open_ch, close_ch in [("{", "}"), ("[", "]")]:
            start = text.find(open_ch)
            end = text.rfind(close_ch)
            if start >= 0 and end > start:
                try:
                    data = json.loads(text[start:end + 1])
                    if isinstance(data, dict) and "questions" in data:
                        return data["questions"]
                    if isinstance(data, list):
                        return data
                except json.JSONDecodeError:
                    pass

        return []
