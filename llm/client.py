# new-agent/llm/client.py
"""OpenAI-compatible LLM and Embedding clients."""

from __future__ import annotations

import json
from typing import AsyncIterator

import openai

from config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL, EMBEDDING_API_BASE, EMBEDDING_API_KEY, EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE


class ChatClient:
    """Async chat completion client (OpenAI-compatible)."""

    def __init__(self, api_base: str = LLM_API_BASE, api_key: str = LLM_API_KEY, model: str = LLM_MODEL):
        self.client = openai.AsyncOpenAI(base_url=api_base, api_key=api_key)
        self.model = model

    async def chat(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        response_format: dict | None = None,
    ) -> str:
        """Send a chat completion request. Returns the full response text."""
        kwargs: dict = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        if stream:
            return await self._stream_chat(kwargs)

        resp = await self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    async def _stream_chat(self, kwargs: dict) -> str:
        """Stream chat and accumulate full text."""
        kwargs["stream"] = True
        full = ""
        async for chunk in await self.client.chat.completions.create(**kwargs):
            delta = chunk.choices[0].delta
            if delta and delta.content:
                full += delta.content
        return full

    async def chat_stream(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Yield text chunks as they arrive."""
        kwargs: dict = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async for chunk in await self.client.chat.completions.create(**kwargs):
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


class EmbeddingClient:
    """Async embedding client (OpenAI-compatible)."""

    def __init__(
        self,
        api_base: str = EMBEDDING_API_BASE,
        api_key: str = EMBEDDING_API_KEY,
        model: str = EMBEDDING_MODEL,
    ):
        self.client = openai.AsyncOpenAI(base_url=api_base, api_key=api_key)
        self.model = model

    async def embed(self, texts: list[str], *, model: str | None = None, batch_size: int = EMBEDDING_BATCH_SIZE) -> list[list[float]]:
        """Get embeddings for a list of texts. Splits into batches to respect API limits."""
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = await self.client.embeddings.create(model=model or self.model, input=batch)
            all_embeddings.extend(item.embedding for item in resp.data)
        return all_embeddings

    async def embed_one(self, text: str, *, model: str | None = None) -> list[float]:
        """Get embedding for a single text."""
        vecs = await self.embed([text], model=model)
        return vecs[0]
