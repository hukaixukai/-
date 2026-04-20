# new-agent/api/routes.py
"""FastAPI routes — REST API for the study companion (ready for web frontend)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse

from models import (
    ChatRequest, ChatResponse,
    ImportRequest, ImportResponse, KnowledgeListResponse,
    ExerciseRequest, ExerciseResponse,
    EvaluateRequest, EvaluateResponse, BatchEvaluateRequest, BatchEvaluateResponse,
    StudentProfileResponse, PlanRequest, PlanResponse,
    SubjectCreateRequest, SubjectListResponse,
)
from chat.session import SessionManager
from knowledge.retriever import KnowledgeBase
from student.memory import StudentMemory
from student.diagnostics import LearningDiagnostics
from student.planner import LearningPlanner
from exercise.generator import ExerciseGenerator
from exercise.evaluator import ExerciseEvaluator
from llm.client import ChatClient, EmbeddingClient

router = APIRouter(prefix="/api", tags=["study-companion"])

# Injected by api_server.py
_chat_client: ChatClient = None  # type: ignore
_embed_client: EmbeddingClient = None  # type: ignore
_session_mgr: SessionManager = None  # type: ignore
_diag: LearningDiagnostics = None  # type: ignore
_planner: LearningPlanner = None  # type: ignore
_gen: ExerciseGenerator = None  # type: ignore
_eval: ExerciseEvaluator = None  # type: ignore


def init(chat_client: ChatClient, embed_client: EmbeddingClient, session_mgr: SessionManager):
    global _chat_client, _embed_client, _session_mgr, _diag, _planner, _gen, _eval
    _chat_client = chat_client
    _embed_client = embed_client
    _session_mgr = session_mgr
    _diag = LearningDiagnostics(chat_client)
    _planner = LearningPlanner(chat_client)
    _gen = ExerciseGenerator(chat_client)
    _eval = ExerciseEvaluator(chat_client)


# ── Chat ──

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send a message to the study companion."""
    session = _session_mgr.get_session(req.subject)
    kb = KnowledgeBase(req.subject, _chat_client, _embed_client)

    # Try RAG first if knowledge base has content
    if kb.store.size > 0:
        rag_results = await kb.retrieve(req.message)
        if rag_results:
            response = await kb.query(req.message)
            sources = [{"source": r.get("source", ""), "score": r.get("score", 0)} for r in rag_results]
            # Also save to chat history
            session.history.append({"role": "user", "content": req.message})
            session.history.append({"role": "assistant", "content": response})
            session.storage.save(req.subject, session.history)
            return ChatResponse(subject=req.subject, response=response, sources=sources)

    # Fallback to direct chat
    response = await session.send(req.message)
    return ChatResponse(subject=req.subject, response=response)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Stream a chat response."""
    session = _session_mgr.get_session(req.subject)

    async def generate():
        async for chunk in session.send_stream(req.message):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── Knowledge Base ──

@router.post("/knowledge/import", response_model=ImportResponse)
async def import_knowledge(req: ImportRequest):
    """Import a file into a subject's knowledge base."""
    # Validate path: must be an existing regular file (prevent path traversal)
    import os
    resolved = os.path.realpath(req.file_path)
    if not os.path.isfile(resolved):
        raise HTTPException(status_code=400, detail="File not found or is not a regular file")
    kb = KnowledgeBase(req.subject, _chat_client, _embed_client)
    count = await kb.import_file(req.file_path)
    if count == 0:
        raise HTTPException(status_code=400, detail="Failed to extract text from file")
    return ImportResponse(subject=req.subject, filename=req.file_path, chunks_added=count)


@router.get("/knowledge/{subject}", response_model=KnowledgeListResponse)
async def list_knowledge(subject: str):
    """List knowledge base sources for a subject."""
    kb = KnowledgeBase(subject, _chat_client, _embed_client)
    return KnowledgeListResponse(subject=subject, sources=kb.list_sources())


@router.delete("/knowledge/{subject}")
async def clear_knowledge(subject: str):
    """Clear a subject's knowledge base."""
    kb = KnowledgeBase(subject, _chat_client, _embed_client)
    kb.clear()
    return {"status": "cleared", "subject": subject}


# ── Exercises ──

@router.post("/exercise/generate", response_model=ExerciseResponse)
async def generate_exercise(req: ExerciseRequest):
    """Generate exercises on a topic."""
    # Get RAG context if available
    kb = KnowledgeBase(req.subject, _chat_client, _embed_client)
    context = ""
    if kb.store.size > 0:
        results = await kb.retrieve(req.topic)
        if results:
            context = "\n\n".join(r["text"] for r in results[:3])

    questions = await _gen.generate(
        req.topic,
        difficulty=req.difficulty,
        question_type=req.question_type,
        count=req.count,
        context=context,
    )
    return ExerciseResponse(subject=req.subject, topic=req.topic, questions=questions)


@router.post("/exercise/evaluate", response_model=EvaluateResponse)
async def evaluate_exercise(req: EvaluateRequest):
    """Evaluate a single student answer."""
    memory = StudentMemory(req.student_id, req.subject)
    feedback = await _eval.evaluate(
        req.question, req.correct_answer, req.student_answer,
        topic=req.topic, memory=memory,
    )
    correct = _eval.check_correct(req.correct_answer, req.student_answer)
    return EvaluateResponse(feedback=feedback, correct=correct)


@router.post("/exercise/evaluate/batch", response_model=BatchEvaluateResponse)
async def evaluate_batch(req: BatchEvaluateRequest):
    """Evaluate multiple student answers."""
    memory = StudentMemory(req.student_id, req.subject)
    try:
        answers = {int(k): v for k, v in req.student_answers.items()}
    except ValueError:
        raise HTTPException(status_code=400, detail="student_answers keys must be integer question IDs")
    results = await _eval.evaluate_batch(
        req.questions, answers, topic=req.topic, memory=memory,
    )
    score = sum(1 for r in results if r["correct"])
    return BatchEvaluateResponse(results=results, score=score, total=len(results))


# ── Student Profile ──

@router.get("/student/{student_id}/{subject}/profile", response_model=StudentProfileResponse)
async def get_profile(student_id: str, subject: str):
    """Get student learning profile."""
    memory = StudentMemory(student_id, subject)
    analysis = _diag.analyze(memory)
    return StudentProfileResponse(
        student_id=student_id,
        subject=subject,
        level=analysis["level"],
        accuracy=analysis["accuracy"],
        weak_points=analysis["weak_points"],
        strong_points=analysis["strong_points"],
        topics=memory.get_topics(),
    )


@router.get("/student/{student_id}/{subject}/diagnosis")
async def get_diagnosis(student_id: str, subject: str):
    """Get LLM-powered learning diagnosis."""
    memory = StudentMemory(student_id, subject)
    diagnosis = await _diag.diagnose(memory)
    return {"diagnosis": diagnosis}


# ── Learning Plan ──

@router.post("/student/plan", response_model=PlanResponse)
async def generate_plan(req: PlanRequest):
    """Generate a personalized learning plan."""
    memory = StudentMemory(req.student_id, req.subject)
    plan = await _planner.generate_plan(memory, req.goal, req.available_time)
    return PlanResponse(plan=plan)


# ── Subjects ──

@router.get("/subjects", response_model=SubjectListResponse)
async def list_subjects():
    """List all subjects with sessions."""
    return SubjectListResponse(subjects=_session_mgr.list_subjects())


@router.post("/subjects")
async def create_subject(req: SubjectCreateRequest):
    """Create/initialize a new subject session."""
    _session_mgr.get_session(req.name)
    return {"status": "created", "subject": req.name}


@router.delete("/subjects/{subject}")
async def delete_subject(subject: str):
    """Delete a subject and all its data."""
    _session_mgr.delete_subject(subject)
    return {"status": "deleted", "subject": subject}
