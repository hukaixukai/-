# new-agent/cli/interface.py
"""Rich-powered interactive CLI for the study companion."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich.columns import Columns
from rich.live import Live
from rich.rule import Rule

from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL, EMBEDDING_API_BASE, EMBEDDING_API_KEY, EMBEDDING_MODEL
from llm.client import ChatClient, EmbeddingClient
from chat.session import SessionManager
from chat.prompts import STUDY_COMPANION_SYSTEM
from knowledge.retriever import KnowledgeBase
from student.memory import StudentMemory
from student.diagnostics import LearningDiagnostics
from student.planner import LearningPlanner
from exercise.generator import ExerciseGenerator
from exercise.evaluator import ExerciseEvaluator

console = Console(legacy_windows=False)


BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║                   [bold cyan]   智 能 学 伴  [/bold cyan]                       ║
║               [dim]Intelligent Study Companion[/dim]                ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""


class CLI:
    """Main CLI application."""

    def __init__(self):
        self.llm = ChatClient()
        self.embedder = EmbeddingClient()
        self.session_mgr = SessionManager(self.llm)
        self.diagnostics = LearningDiagnostics(self.llm)
        self.planner = LearningPlanner(self.llm)
        self.generator = ExerciseGenerator(self.llm)
        self.evaluator = ExerciseEvaluator(self.llm)
        self.student_id = "default"
        self.current_subject: str | None = None

    def run(self):
        """Main entry point."""
        console.print(Panel(BANNER, border_style="cyan", padding=(0, 2)))
        self._select_or_create_subject()

        while True:
            try:
                self._main_menu()
            except KeyboardInterrupt:
                console.print("\n[yellow]再见！[/yellow]")
                break
            except EOFError:
                break

    def _select_or_create_subject(self):
        """Initial subject selection."""
        console.print()
        subjects = self.session_mgr.list_subjects()

        if subjects:
            console.print("[bold]已有的课程：[/bold]")
            for i, s in enumerate(subjects, 1):
                console.print(f"  [cyan]{i}[/cyan]. {s}")
            console.print(f"  [cyan]0[/cyan]. 创建新课程")
            console.print()

            choice = Prompt.ask("请选择课程编号", default="0")
            try:
                idx = int(choice)
            except ValueError:
                console.print("[red]请输入有效的数字[/red]")
                return
            if 0 < idx <= len(subjects):
                self.current_subject = subjects[idx - 1]
                self.session_mgr.set_current(self.current_subject)
                console.print(f"[green]已选择课程: {self.current_subject}[/green]")
                return

        # Create new subject
        name = Prompt.ask("请输入课程名称（如：数据结构、Python编程）")
        self.current_subject = name
        self.session_mgr.set_current(name)
        console.print(f"[green]已创建课程: {name}[/green]")

    def _main_menu(self):
        """Display and handle main menu."""
        console.print()
        console.print(Rule(style="cyan"))
        table = Table(title=f"当前课程: [bold cyan]{self.current_subject}[/bold cyan]", show_header=False, border_style="dim")
        table.add_column("编号", style="cyan", width=6)
        table.add_column("功能")
        table.add_row("1", "  智能问答（对话模式）")
        table.add_row("2", "  知识库管理")
        table.add_row("3", "  学情诊断")
        table.add_row("4", "  练习与测验")
        table.add_row("5", "  个性化学习计划")
        table.add_row("6", "  切换课程")
        table.add_row("7", "  学生档案设置")
        table.add_row("0", "  退出")
        console.print(table)

        choice = Prompt.ask("请选择功能", choices=["0", "1", "2", "3", "4", "5", "6", "7"], default="1")

        actions = {
            "1": self._chat_mode,
            "2": self._knowledge_menu,
            "3": self._diagnostics_menu,
            "4": self._exercise_menu,
            "5": self._plan_menu,
            "6": self._switch_subject,
            "7": self._student_settings,
            "0": lambda: self._exit(),
        }
        actions[choice]()

    @staticmethod
    def _exit():
        raise KeyboardInterrupt()

    # ── Chat ──

    def _chat_mode(self):
        """Interactive chat with the study companion."""
        session = self.session_mgr.get_current()
        if not session:
            console.print("[red]请先选择课程[/red]")
            return

        kb = KnowledgeBase(self.current_subject, self.llm, self.embedder)
        has_knowledge = kb.store.size > 0

        console.print()
        console.print(Panel(
            f"[bold]对话模式[/bold] | 课程: {self.current_subject} | 知识库: {'已加载' if has_knowledge else '未加载'}\n"
            "输入问题开始对话，输入 [cyan]/quit[/cyan] 退出，[cyan]/clear[/cyan] 清空历史",
            border_style="green",
        ))
        console.print()

        while True:
            try:
                user_input = Prompt.ask("[bold green]你[/bold green]")
            except (KeyboardInterrupt, EOFError):
                break

            if not user_input.strip():
                continue
            if user_input.strip() == "/quit":
                break
            if user_input.strip() == "/clear":
                session.clear_history()
                console.print("[yellow]对话历史已清空[/yellow]")
                continue

            # Log question to memory
            memory = StudentMemory(self.student_id, self.current_subject)
            memory.log_question(user_input)

            console.print()
            # Stream response
            asyncio.run(self._stream_chat(session, user_input, kb))
            console.print()

    async def _stream_chat(self, session, user_input: str, kb: KnowledgeBase):
        """Stream a chat response with Rich formatting."""
        # Try RAG first
        if kb.store.size > 0:
            results = await kb.retrieve(user_input)
            if results:
                console.print(f"[dim]  从知识库检索到 {len(results)} 条相关资料[/dim]")
                console.print()
                response = await kb.query(user_input)
                # Also add to history
                session.history.append({"role": "user", "content": user_input})
                session.history.append({"role": "assistant", "content": response})
                session.storage.save(session.subject, session.history)
                # Display with sources
                console.print(Panel(Markdown(response), title="[bold blue]学伴[/bold blue]", border_style="blue"))
                # Show sources
                sources = set(r.get("source", "") for r in results if r.get("source"))
                if sources:
                    console.print(f"[dim]  参考来源: {', '.join(sources)}[/dim]")
                return

        # Direct chat with streaming
        console.print("[bold blue]学伴[/bold blue]: ", end="")
        full = ""
        async for chunk in session.send_stream(user_input):
            console.print(chunk, end="", highlight=False)
            full += chunk
        console.print()

    # ── Knowledge Base ──

    def _knowledge_menu(self):
        """Knowledge base management."""
        console.print()
        console.print(Panel("[bold]知识库管理[/bold]", border_style="magenta"))
        console.print("  [cyan]1[/cyan]. 导入文件（PDF/图片/文本）")
        console.print("  [cyan]2[/cyan]. 导入目录")
        console.print("  [cyan]3[/cyan]. 查看已导入资料")
        console.print("  [cyan]4[/cyan]. 清空知识库")
        console.print("  [cyan]0[/cyan]. 返回")

        choice = Prompt.ask("请选择", choices=["0", "1", "2", "3", "4"], default="1")

        kb = KnowledgeBase(self.current_subject, self.llm, self.embedder)

        if choice == "1":
            path = Prompt.ask("请输入文件路径")
            if not Path(path).exists():
                console.print("[red]文件不存在[/red]")
                return
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                progress.add_task("正在导入并生成向量...", total=None)
                count = asyncio.run(kb.import_file(path))
            if count > 0:
                console.print(f"[green]导入成功！共 {count} 个文本块[/green]")
            else:
                console.print("[red]导入失败，无法提取文本[/red]")

        elif choice == "2":
            path = Prompt.ask("请输入目录路径")
            if not Path(path).is_dir():
                console.print("[red]目录不存在[/red]")
                return
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                progress.add_task("正在批量导入...", total=None)
                results = asyncio.run(kb.import_directory(path))
            if results:
                table = Table(title="导入结果", border_style="green")
                table.add_column("文件", style="cyan")
                table.add_column("文本块数", justify="right")
                for fname, count in results.items():
                    table.add_row(fname, str(count))
                console.print(table)
            else:
                console.print("[yellow]未找到可导入的文件[/yellow]")

        elif choice == "3":
            sources = kb.list_sources()
            if not sources:
                console.print("[yellow]知识库为空[/yellow]")
                return
            table = Table(title=f"知识库 - {self.current_subject}", border_style="cyan")
            table.add_column("文件名", style="cyan")
            table.add_column("文本块数", justify="right")
            for s in sources:
                table.add_row(s.get("filename", ""), str(s.get("chunks", 0)))
            console.print(table)
            console.print(f"[dim]向量总数: {kb.store.size}[/dim]")

        elif choice == "4":
            if Confirm.ask("确定清空知识库？"):
                kb.clear()
                console.print("[green]知识库已清空[/green]")

    # ── Diagnostics ──

    def _diagnostics_menu(self):
        """Learning diagnostics display."""
        memory = StudentMemory(self.student_id, self.current_subject)
        analysis = self.diagnostics.analyze(memory)

        console.print()
        console.print(Panel(f"[bold]学情诊断[/bold] - {self.current_subject}", border_style="yellow"))

        # Level & accuracy
        level_colors = {"优秀": "green", "良好": "cyan", "一般": "yellow", "薄弱": "red"}
        level_color = level_colors.get(analysis["level"], "white")
        console.print(f"  掌握水平: [{level_color}]{analysis['level']}[/{level_color}]")
        console.print(f"  总正确率: {analysis['accuracy']:.0%}")
        console.print(f"  测验均分: {analysis['quiz_average']:.0%}")
        console.print(f"  总互动次数: {analysis['total_interactions']}")

        # Weak/strong points
        if analysis["weak_points"]:
            console.print(f"\n  [red]薄弱知识点:[/red]")
            for wp in analysis["weak_points"]:
                console.print(f"    - {wp}")
        if analysis["strong_points"]:
            console.print(f"\n  [green]掌握较好:[/green]")
            for sp in analysis["strong_points"]:
                console.print(f"    - {sp}")

        # Topic details
        topics = memory.get_topics()
        if topics:
            console.print()
            table = Table(title="知识点详情", border_style="dim")
            table.add_column("知识点", style="cyan")
            table.add_column("正确", justify="right", style="green")
            table.add_column("错误", justify="right", style="red")
            table.add_column("正确率", justify="right")
            for name, stats in topics.items():
                total = stats["correct"] + stats["wrong"]
                rate = f"{stats['correct']/total:.0%}" if total > 0 else "-"
                table.add_row(name, str(stats["correct"]), str(stats["wrong"]), rate)
            console.print(table)

        # Suggestions
        if analysis["suggestions"]:
            console.print(f"\n  [bold]建议:[/bold]")
            for s in analysis["suggestions"]:
                console.print(f"    {s}")

        # Ask for LLM diagnosis
        if analysis["total_interactions"] > 0 and Confirm.ask("\n获取详细AI诊断？"):
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                progress.add_task("AI正在分析...", total=None)
                diagnosis = asyncio.run(self.diagnostics.diagnose(memory))
            console.print()
            console.print(Panel(Markdown(diagnosis), title="[bold yellow]AI 诊断报告[/bold yellow]", border_style="yellow"))

    # ── Exercise ──

    def _exercise_menu(self):
        """Exercise generation and interactive practice."""
        console.print()
        console.print(Panel("[bold]练习与测验[/bold]", border_style="magenta"))
        console.print("  [cyan]1[/cyan]. 选择题")
        console.print("  [cyan]2[/cyan]. 填空题")
        console.print("  [cyan]3[/cyan]. 简答题")
        console.print("  [cyan]4[/cyan]. 编程题")
        console.print("  [cyan]0[/cyan]. 返回")

        type_map = {"1": "choice", "2": "fill", "3": "short_answer", "4": "coding"}
        choice = Prompt.ask("请选择题型", choices=["0", "1", "2", "3", "4"], default="1")
        if choice == "0":
            return

        q_type = type_map[choice]
        topic = Prompt.ask("请输入练习主题")
        difficulty = Prompt.ask("难度", choices=["easy", "medium", "hard"], default="medium")
        count = IntPrompt.ask("题目数量", default=3)

        # Get RAG context
        kb = KnowledgeBase(self.current_subject, self.llm, self.embedder)
        context = ""
        if kb.store.size > 0:
            results = asyncio.run(kb.retrieve(topic))
            if results:
                context = "\n\n".join(r["text"] for r in results[:3])

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            progress.add_task("正在生成题目...", total=None)
            questions = asyncio.run(self.generator.generate(
                topic, difficulty=difficulty, question_type=q_type, count=count, context=context,
            ))

        if not questions:
            console.print("[red]题目生成失败[/red]")
            return

        memory = StudentMemory(self.student_id, self.current_subject)
        correct_count = 0

        for q in questions:
            console.print()
            console.print(Rule(style="dim"))
            q_text = q.get("question", "")
            q_id = q.get("id", 0)

            # Display question
            console.print(Panel(
                Markdown(q_text),
                title=f"[bold]第 {q_id} 题[/bold] [{q.get('difficulty', '')}]",
                border_style="cyan",
            ))

            # Show options for choice questions
            options = q.get("options", [])
            if options:
                for opt in options:
                    console.print(f"  {opt}")

            # Get student answer
            console.print()
            student_answer = Prompt.ask("[bold green]你的答案[/bold green]")

            # Evaluate
            correct_answer = str(q.get("answer", ""))
            is_correct = self.evaluator.check_correct(correct_answer, student_answer)

            # Show answer and explanation
            if is_correct:
                correct_count += 1
                console.print("[bold green]  ✓ 正确！[/bold green]")
            else:
                console.print(f"[bold red]  ✗ 错误[/bold red]  正确答案: [cyan]{correct_answer}[/cyan]")

            explanation = q.get("explanation", "")
            if explanation:
                console.print(f"  [dim]解析: {explanation}[/dim]")

            # Record to memory
            q_topic = q.get("topic", topic)
            memory.record_topic(q_topic, is_correct)
            if not is_correct:
                memory.record_error(q_topic, q_text, student_answer, correct_answer)

        # Summary
        console.print()
        console.print(Rule(style="cyan"))
        console.print(Panel(
            f"[bold]练习完成！[/bold]\n"
            f"正确: [green]{correct_count}[/green] / {len(questions)}  "
            f"正确率: [cyan]{correct_count/len(questions):.0%}[/cyan]",
            border_style="cyan",
        ))
        memory.record_quiz(topic, correct_count, len(questions))

    # ── Learning Plan ──

    def _plan_menu(self):
        """Generate personalized learning plan."""
        console.print()
        memory = StudentMemory(self.student_id, self.current_subject)
        analysis = self.diagnostics.analyze(memory)

        console.print(Panel(
            f"[bold]个性化学习计划[/bold]\n"
            f"当前水平: {analysis['level']} | 正确率: {analysis['accuracy']:.0%}\n"
            f"薄弱知识点: {', '.join(analysis['weak_points']) or '暂无'}",
            border_style="green",
        ))

        goal = Prompt.ask("学习目标", default="掌握本课程核心知识")
        time_avail = Prompt.ask("可用时间", default="每天2小时")

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            progress.add_task("正在生成学习计划...", total=None)
            plan = asyncio.run(self.planner.generate_plan(memory, goal, time_avail))

        console.print()
        console.print(Panel(Markdown(plan), title="[bold green]学习计划[/bold green]", border_style="green"))

    # ── Subject Management ──

    def _switch_subject(self):
        """Switch or create a subject."""
        subjects = self.session_mgr.list_subjects()
        console.print()
        console.print("[bold]课程列表：[/bold]")
        for i, s in enumerate(subjects, 1):
            marker = " [cyan]← 当前[/cyan]" if s == self.current_subject else ""
            console.print(f"  {i}. {s}{marker}")
        console.print(f"  0. 创建新课程")

        choice = Prompt.ask("选择编号")
        try:
            idx = int(choice)
        except ValueError:
            console.print("[red]请输入有效的数字[/red]")
            return
        if idx == 0:
            name = Prompt.ask("新课程名称")
            self.current_subject = name
            self.session_mgr.set_current(name)
            console.print(f"[green]已创建: {name}[/green]")
        elif 0 < idx <= len(subjects):
            self.current_subject = subjects[idx - 1]
            self.session_mgr.set_current(self.current_subject)
            console.print(f"[green]已切换到: {self.current_subject}[/green]")

    # ── Student Settings ──

    def _student_settings(self):
        """Configure student ID."""
        console.print()
        console.print(f"当前学生ID: [cyan]{self.student_id}[/cyan]")
        new_id = Prompt.ask("输入新的学生ID（留空不变）", default="")
        if new_id:
            self.student_id = new_id
            console.print(f"[green]学生ID已更新为: {self.student_id}[/green]")
