# new-agent/models.py
"""Pydantic schemas for API requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Chat ---

class ChatRequest(BaseModel):
    subject: str = Field(..., description="Subject/course name")
    message: str = Field(..., description="Student's message")
    student_id: str = Field(default="default", description="Student identifier")


class ChatResponse(BaseModel):
    subject: str
    response: str
    sources: list[dict] = Field(default_factory=list)


# --- Knowledge Base ---

class ImportRequest(BaseModel):
    subject: str
    file_path: str = Field(..., description="Absolute path to the file to import")


class ImportResponse(BaseModel):
    subject: str
    filename: str
    chunks_added: int


class KnowledgeListResponse(BaseModel):
    subject: str
    sources: list[dict]


# --- Exercise ---

class ExerciseRequest(BaseModel):
    subject: str
    topic: str
    difficulty: str = "medium"
    question_type: str = "choice"
    count: int = 5
    student_id: str = "default"


class ExerciseResponse(BaseModel):
    subject: str
    topic: str
    questions: list[dict]


class EvaluateRequest(BaseModel):
    subject: str
    topic: str
    question: str
    correct_answer: str
    student_answer: str
    student_id: str = "default"


class EvaluateResponse(BaseModel):
    feedback: str
    correct: bool


class BatchEvaluateRequest(BaseModel):
    subject: str
    topic: str
    questions: list[dict]
    student_answers: dict[str, str]  # question_id (str) -> answer
    student_id: str = "default"


class BatchEvaluateResponse(BaseModel):
    results: list[dict]
    score: int
    total: int


# --- Student ---

class StudentProfileResponse(BaseModel):
    student_id: str
    subject: str
    level: str
    accuracy: float
    weak_points: list[str]
    strong_points: list[str]
    topics: dict


class PlanRequest(BaseModel):
    subject: str
    goal: str = "掌握本课程核心知识"
    available_time: str = "每天2小时"
    student_id: str = "default"


class PlanResponse(BaseModel):
    plan: str


# --- Subject Management ---

class SubjectCreateRequest(BaseModel):
    name: str = Field(..., description="Subject/course name")


class SubjectListResponse(BaseModel):
    subjects: list[str]
