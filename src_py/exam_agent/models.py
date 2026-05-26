from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class StudyProfile(BaseModel):
    grade: str
    current_level: str
    weak_points: List[str] = Field(default_factory=list)
    recent_score: Optional[str] = None


class Expectation(BaseModel):
    target: str
    difficulty: str
    paper_length_min: int


class IntakeRequest(BaseModel):
    subject: str
    exam_mode: Literal["new_gaokao", "old_gaokao"]
    study_profile: StudyProfile
    expectation: Expectation


class QuestionRow(BaseModel):
    topic: str
    question_no: Optional[str] = None
    kaodian_no: Optional[str] = None
    kaodian_name: Optional[str] = None
    stem_md: str
    analysis_md: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)


class PaperSection(BaseModel):
    name: str
    count: int
    questions: List[QuestionRow]


class Paper(BaseModel):
    title: str
    exam_mode: str
    request: IntakeRequest
    sections: List[PaperSection]
    stats: dict
