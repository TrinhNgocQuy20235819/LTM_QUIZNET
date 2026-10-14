"""
models.py - Định nghĩa các Schema dữ liệu Pydantic cho API
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class CreateRoomRequest(BaseModel):
    room_name: str = Field(..., min_length=2, max_length=100, description="Tên phòng thi")
    host_name: str = Field(..., min_length=2, max_length=50, description="Tên người tạo phòng")
    duration_minutes: int = Field(..., ge=1, le=180, description="Thời gian làm bài (phút)")
    easy_count: int = Field(default=5, ge=0, description="Số câu hỏi Dễ")
    medium_count: int = Field(default=3, ge=0, description="Số câu hỏi Trung bình")
    hard_count: int = Field(default=2, ge=0, description="Số câu hỏi Khó")

class StartPracticeRequest(BaseModel):
    user_name: str = Field(..., min_length=2, max_length=50, description="Tên người luyện tập")
    duration_minutes: int = Field(default=10, ge=1, le=120, description="Thời gian làm bài (phút)")
    easy_count: int = Field(default=5, ge=0, description="Số câu hỏi Dễ")
    medium_count: int = Field(default=3, ge=0, description="Số câu hỏi Trung bình")
    hard_count: int = Field(default=2, ge=0, description="Số câu hỏi Khó")
    category: Optional[str] = Field(default="all", description="Chủ đề câu hỏi")

class SubmitPracticeRequest(BaseModel):
    user_name: str
    question_ids: List[int]
    answers: Dict[str, str] # { "1": "A", "2": "C" }
    duration_seconds: int

class AddQuestionRequest(BaseModel):
    content: str = Field(..., min_length=5)
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str = Field(..., pattern="^[A-Da-d]$")
    difficulty: str = Field(..., pattern="^(easy|medium|hard)$")
    category: str
    explanation: Optional[str] = ""
