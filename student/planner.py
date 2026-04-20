# new-agent/student/planner.py
"""Personalized learning plan generation."""

from __future__ import annotations

from chat.prompts import PLANNING_SYSTEM
from llm.client import ChatClient
from student.memory import StudentMemory
from student.diagnostics import LearningDiagnostics


class LearningPlanner:
    """Generates personalized learning plans based on student diagnostics."""

    def __init__(self, llm: ChatClient):
        self.llm = llm
        self.diagnostics = LearningDiagnostics(llm)

    async def generate_plan(
        self,
        memory: StudentMemory,
        goal: str = "掌握本课程核心知识",
        available_time: str = "每天2小时",
    ) -> str:
        """Generate a personalized learning plan."""
        analysis = self.diagnostics.analyze(memory)

        system = PLANNING_SYSTEM.format(
            level=analysis["level"],
            goal=goal,
            available_time=available_time,
            weak_points=", ".join(analysis["weak_points"]) or "暂无明确薄弱点",
            strong_points=", ".join(analysis["strong_points"]) or "暂无",
        )

        # Include recent context
        recent_errors = memory.get_errors(5)
        context_parts = []
        if recent_errors:
            context_parts.append("近期错误：")
            for e in recent_errors:
                context_parts.append(f"  - [{e['topic']}] {e['question'][:60]}")

        context = "\n".join(context_parts) if context_parts else "暂无近期错误记录"

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"请为我制定学习计划。\n\n补充信息：\n{context}"},
        ]

        return await self.llm.chat(messages, temperature=0.5)

    async def generate_quick_plan(self, subject: str, topics: list[str], days: int = 7) -> str:
        """Generate a quick study plan for specific topics without full diagnostics."""
        topic_list = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(topics))
        prompt = f"""请为"{subject}"课程制定一个{days}天的学习计划。

需要学习的知识点：
{topic_list}

要求：
1. 每天安排2-3个知识点
2. 优先安排基础知识点
3. 包含复习和练习时间
4. 用表格形式展示"""

        return await self.llm.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.5,
        )
