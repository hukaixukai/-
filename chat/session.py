# new-agent/chat/session.py
"""Chat session management with per-subject isolation."""

from __future__ import annotations

import json
from pathlib import Path

from config import SUBJECTS_DIR
from chat.compressor import HistoryCompressor, HistoryStorage
from chat.prompts import STUDY_COMPANION_SYSTEM
from llm.client import ChatClient


class ChatSession:
    """A chat session tied to a specific subject."""

    def __init__(self, subject: str, llm: ChatClient, data_dir: Path | None = None):
        self.subject = subject
        self.llm = llm
        self.compressor = HistoryCompressor(llm)

        base = data_dir or SUBJECTS_DIR / subject
        self.storage = HistoryStorage(base)

        # Initialize history from disk
        self.history: list[dict] = self.storage.load(subject)

    async def send(self, user_message: str, *, system_override: str | None = None) -> str:
        """Send a message and get a response. Manages history automatically."""
        # Add user message
        self.history.append({"role": "user", "content": user_message})

        # Compress if needed
        self.history = await self.compressor.maybe_compress(self.history)

        # Build messages with system prompt (merge with any compressed summary)
        system = system_override or STUDY_COMPANION_SYSTEM
        compressed_system = self._extract_compressed_system()
        if compressed_system:
            system = f"{system}\n\n{compressed_system}"
        messages = [{"role": "system", "content": system}] + self._history_without_compressed_system()

        # Get response
        response = await self.llm.chat(messages)

        # Add assistant response
        self.history.append({"role": "assistant", "content": response})

        # Persist
        self.storage.save(self.subject, self.history)

        return response

    async def send_stream(self, user_message: str, *, system_override: str | None = None):
        """Send a message and stream the response. Returns an async generator."""
        self.history.append({"role": "user", "content": user_message})
        self.history = await self.compressor.maybe_compress(self.history)

        system = system_override or STUDY_COMPANION_SYSTEM
        messages = [{"role": "system", "content": system}] + self._history_without_compressed_system()

        full_response = ""
        try:
            async for chunk in self.llm.chat_stream(messages):
                full_response += chunk
                yield chunk
        finally:
            if full_response:
                self.history.append({"role": "assistant", "content": full_response})
            self.storage.save(self.subject, self.history)

    def _extract_compressed_system(self) -> str | None:
        """Extract compressed summary from history if present."""
        if self.history and self.history[0].get("metadata", {}).get("compressed"):
            return self.history[0].get("content")
        return None

    def _history_without_compressed_system(self) -> list[dict]:
        """Return history with compressed system messages filtered out."""
        return [m for m in self.history if not m.get("metadata", {}).get("compressed")]

    def clear_history(self) -> None:
        """Clear chat history for this subject."""
        self.history = []
        self.storage.clear(self.subject)


class SessionManager:
    """Manages multiple subject-specific chat sessions."""

    def __init__(self, llm: ChatClient):
        self.llm = llm
        self._sessions: dict[str, ChatSession] = {}
        self._current_subject: str | None = None

    def get_session(self, subject: str) -> ChatSession:
        """Get or create a chat session for a subject."""
        if subject not in self._sessions:
            self._sessions[subject] = ChatSession(subject, self.llm)
        return self._sessions[subject]

    def set_current(self, subject: str) -> None:
        self._current_subject = subject

    def get_current(self) -> ChatSession | None:
        if self._current_subject:
            return self.get_session(self._current_subject)
        return None

    def list_subjects(self) -> list[str]:
        """List all subjects that have stored history."""
        subjects = set()
        if SUBJECTS_DIR.exists():
            for f in SUBJECTS_DIR.iterdir():
                if f.is_dir():
                    subjects.add(f.name)
        # Also include in-memory sessions
        subjects.update(self._sessions.keys())
        return sorted(subjects)

    def delete_subject(self, subject: str) -> bool:
        """Delete a subject session and its history."""
        session = self._sessions.pop(subject, None)
        if session:
            session.clear_history()
        # Clean up directory
        subject_dir = SUBJECTS_DIR / subject
        if subject_dir.exists():
            import shutil
            shutil.rmtree(subject_dir)
            return True
        return session is not None
