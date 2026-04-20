# new-agent/chat/compressor.py
"""Chat history compression — summarize old messages to keep context manageable."""

from __future__ import annotations

import json
from pathlib import Path

from config import COMPRESSION_THRESHOLD, MAX_HISTORY_TOKENS
from chat.prompts import HISTORY_COMPRESSION_SYSTEM
from llm.client import ChatClient


class HistoryCompressor:
    """Compresses older chat history when message count exceeds threshold."""

    def __init__(self, llm: ChatClient):
        self.llm = llm

    async def maybe_compress(self, history: list[dict]) -> list[dict]:
        """Compress history if it exceeds the threshold.

        Returns a new history list where old messages are replaced by a summary.
        The structure: [{"role": "system", "content": "<summary>"}, ...recent_messages]
        """
        if len(history) <= COMPRESSION_THRESHOLD:
            return history

        # Split: older messages to compress, recent messages to keep
        split_at = len(history) - COMPRESSION_THRESHOLD // 2
        older = history[:split_at]
        recent = history[split_at:]

        # Build text from older messages
        history_text = self._messages_to_text(older)

        # Check if there's already a compressed summary in older messages
        existing_summary = None
        for msg in older:
            if msg.get("role") == "system" and msg.get("metadata", {}).get("compressed"):
                existing_summary = msg["content"]
                break

        if existing_summary:
            # Re-compress: merge existing summary + remaining older messages
            non_summary_older = [m for m in older if not (m.get("role") == "system" and m.get("metadata", {}).get("compressed"))]
            if non_summary_older:
                new_text = self._messages_to_text(non_summary_older)
                history_text = f"之前的摘要：\n{existing_summary}\n\n新的对话：\n{new_text}"
            else:
                history_text = existing_summary

        # Use LLM to generate compressed summary
        prompt = HISTORY_COMPRESSION_SYSTEM.format(history=history_text)
        summary = await self.llm.chat(
            [{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000,
        )

        compressed_msg = {
            "role": "system",
            "content": f"[历史对话摘要]\n{summary}",
            "metadata": {"compressed": True},
        }

        return [compressed_msg] + recent

    def _messages_to_text(self, messages: list[dict]) -> str:
        """Convert message list to readable text."""
        lines = []
        for msg in messages:
            if msg.get("metadata", {}).get("compressed"):
                continue  # skip compressed summary messages
            role = "学生" if msg.get("role") == "user" else "学伴"
            content = msg.get("content", "")
            lines.append(f"{role}: {content}")
        return "\n".join(lines)


class HistoryStorage:
    """Persists chat history to disk (JSON files)."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, subject: str) -> Path:
        return self.base_dir / f"{subject}_history.json"

    def load(self, subject: str) -> list[dict]:
        path = self._path(subject)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return []

    def save(self, subject: str, history: list[dict]) -> None:
        path = self._path(subject)
        path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    def append(self, subject: str, role: str, content: str) -> list[dict]:
        history = self.load(subject)
        history.append({"role": role, "content": content})
        self.save(subject, history)
        return history

    def clear(self, subject: str) -> None:
        path = self._path(subject)
        if path.exists():
            path.unlink()
