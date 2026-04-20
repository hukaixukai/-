# new-agent/knowledge/retriever.py
"""RAG retriever: embed query, retrieve context, generate grounded answer."""

from __future__ import annotations

from pathlib import Path

from config import CHUNK_SIZE, CHUNK_OVERLAP, RETRIEVAL_TOP_K, SUBJECTS_DIR
from knowledge.loader import load_and_chunk
from knowledge.vectorstore import VectorStore, get_subject_vector_dir
from knowledge import vectorstore as vs_module
from chat.prompts import RAG_QA_SYSTEM
from llm.client import ChatClient, EmbeddingClient


class KnowledgeBase:
    """Per-subject knowledge base with RAG retrieval."""

    def __init__(self, subject: str, llm: ChatClient, embedder: EmbeddingClient):
        self.subject = subject
        self.llm = llm
        self.embedder = embedder
        self.store_dir = get_subject_vector_dir(subject)
        self.store = VectorStore.load(self.store_dir)
        # Track imported file names
        self.manifest_path = SUBJECTS_DIR / subject / "manifest.json"

    async def import_file(self, file_path: str | Path, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> int:
        """Import a document into the knowledge base. Returns number of chunks added."""
        chunks = load_and_chunk(file_path, chunk_size, overlap)
        if not chunks:
            return 0

        texts = [c["text"] for c in chunks]
        embeddings = await self.embedder.embed(texts)
        self.store.add(embeddings, chunks)
        self.store.save(self.store_dir)

        # Update manifest
        self._update_manifest(Path(file_path).name, len(chunks))
        return len(chunks)

    async def import_directory(self, dir_path: str | Path, extensions: set[str] | None = None) -> dict[str, int]:
        """Import all supported files from a directory."""
        if extensions is None:
            extensions = {".pdf", ".txt", ".md", ".py", ".jpg", ".png"}
        results = {}
        for f in sorted(Path(dir_path).iterdir()):
            if f.is_file() and f.suffix.lower() in extensions:
                count = await self.import_file(f)
                results[f.name] = count
        return results

    async def retrieve(self, query: str, top_k: int = RETRIEVAL_TOP_K) -> list[dict]:
        """Retrieve relevant chunks for a query."""
        query_vec = await self.embedder.embed_one(query)
        return self.store.query(query_vec, top_k)

    async def query(self, question: str, top_k: int = RETRIEVAL_TOP_K) -> str:
        """RAG: retrieve context and generate a grounded answer."""
        results = await self.retrieve(question, top_k)
        if not results:
            return "知识库中暂无相关内容，请先导入课程资料。"

        # Build context from retrieved chunks
        context_parts = []
        for i, r in enumerate(results):
            source = r.get("source", "未知")
            score = r.get("score", 0)
            context_parts.append(f"[参考资料 {i+1} - 来源: {source} (相关度: {score:.2f})]\n{r['text']}")
        context = "\n\n".join(context_parts)

        # Generate answer with RAG prompt
        system = RAG_QA_SYSTEM.format(context=context)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]
        return await self.llm.chat(messages)

    def list_sources(self) -> list[dict]:
        """List all imported sources and their chunk counts."""
        if self.manifest_path.exists():
            import json
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return []

    def clear(self) -> None:
        """Clear the knowledge base."""
        self.store = VectorStore()
        if self.store_dir.exists():
            import shutil
            shutil.rmtree(self.store_dir)
        if self.manifest_path.exists():
            self.manifest_path.unlink()

    def _update_manifest(self, filename: str, chunk_count: int) -> None:
        import json
        manifest = self.list_sources()
        # Remove old entry for same file
        manifest = [m for m in manifest if m.get("filename") != filename]
        manifest.append({"filename": filename, "chunks": chunk_count})
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
