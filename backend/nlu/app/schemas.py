"""
NLU Service Schemas
Pydantic 모델 정의
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class NLURequest(BaseModel):
    """NLU 분석 요청"""
    text: str = Field(..., min_length=1, max_length=1000, description="분석할 텍스트")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "내일 오후 3시에 회의 일정 잡아줘"
            }
        }


class IntentInfo(BaseModel):
    """의도 정보"""
    name: str = Field(..., description="의도 이름")
    confidence: float = Field(..., ge=0.0, le=1.0, description="신뢰도")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "schedule_add",
                "confidence": 0.92
            }
        }


class EntityInfo(BaseModel):
    """엔티티 정보"""
    type: str = Field(..., description="엔티티 타입")
    value: str = Field(..., description="추출된 값")
    start: int = Field(default=0, description="시작 위치")
    end: int = Field(default=0, description="종료 위치")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "date",
                "value": "내일",
                "start": 0,
                "end": 2
            }
        }


class NLUResponse(BaseModel):
    """NLU 분석 응답"""
    text: str = Field(..., description="원본 텍스트")
    intent: IntentInfo = Field(..., description="분류된 의도")
    entities: List[EntityInfo] = Field(default=[], description="추출된 엔티티 목록")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "내일 오후 3시에 회의 일정 잡아줘",
                "intent": {
                    "name": "schedule_add",
                    "confidence": 0.92
                },
                "entities": [
                    {"type": "date", "value": "내일", "start": 0, "end": 2},
                    {"type": "time", "value": "오후 3시", "start": 3, "end": 8}
                ]
            }
        }


class HealthResponse(BaseModel):
    """서비스 상태 응답"""
    status: str = Field(..., description="서비스 상태")
    service: str = Field(..., description="서비스 이름")
    model_loaded: bool = Field(..., description="모델 로드 여부")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "nlu",
                "model_loaded": True
            }
        }


