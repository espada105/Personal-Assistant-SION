"""
Task Executor Service Schemas
Pydantic 모델 정의
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    """작업 실행 요청"""
    intent: str = Field(..., description="실행할 작업 의도")
    entities: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="추출된 엔티티 (작업 파라미터)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "intent": "schedule_add",
                "entities": {
                    "date": "내일",
                    "time": "오후 3시",
                    "title": "회의"
                }
            }
        }


class TaskResponse(BaseModel):
    """작업 실행 응답"""
    success: bool = Field(..., description="성공 여부")
    intent: str = Field(..., description="실행된 의도")
    action: str = Field(..., description="실행된 액션")
    result: Optional[Any] = Field(default=None, description="작업 결과")
    message: str = Field(..., description="결과 메시지")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "intent": "schedule_add",
                "action": "add",
                "result": {
                    "event_id": "abc123",
                    "title": "회의",
                    "start": "2024-01-15T15:00:00"
                },
                "message": "작업이 성공적으로 완료되었습니다."
            }
        }


class ChatRequest(BaseModel):
    """LLM 대화 요청"""
    message: str = Field(..., min_length=1, max_length=4000, description="사용자 메시지")
    conversation_id: Optional[str] = Field(
        default=None, 
        description="대화 세션 ID (연속 대화 시)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "파이썬에서 리스트와 튜플의 차이점은 뭐야?",
                "conversation_id": None
            }
        }


class ChatResponse(BaseModel):
    """LLM 대화 응답"""
    message: str = Field(..., description="LLM 응답")
    conversation_id: Optional[str] = Field(
        default=None, 
        description="대화 세션 ID"
    )
    tokens_used: int = Field(default=0, description="사용된 토큰 수")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "리스트와 튜플의 주요 차이점은...",
                "conversation_id": "conv_123",
                "tokens_used": 150
            }
        }


class HealthResponse(BaseModel):
    """서비스 상태 응답"""
    status: str = Field(..., description="서비스 상태")
    service: str = Field(..., description="서비스 이름")
    handlers_loaded: List[str] = Field(..., description="로드된 핸들러 목록")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "task_executor",
                "handlers_loaded": ["email", "calendar", "llm"]
            }
        }


