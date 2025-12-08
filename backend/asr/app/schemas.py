"""
ASR Service Schemas
Pydantic 모델 정의
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TranscriptionSegment(BaseModel):
    """음성 인식 세그먼트"""
    start: float = Field(..., description="시작 시간 (초)")
    end: float = Field(..., description="종료 시간 (초)")
    text: str = Field(..., description="인식된 텍스트")


class TranscriptionResponse(BaseModel):
    """음성 인식 응답"""
    text: str = Field(..., description="전체 인식 텍스트")
    language: str = Field(default="ko", description="감지된 언어")
    duration: float = Field(default=0.0, description="오디오 길이 (초)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="신뢰도")
    segments: Optional[List[TranscriptionSegment]] = Field(
        default=None, 
        description="세그먼트별 상세 정보"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text": "안녕하세요. 오늘 일정을 알려주세요.",
                "language": "ko",
                "duration": 3.5,
                "confidence": 0.95,
                "segments": [
                    {"start": 0.0, "end": 1.5, "text": "안녕하세요."},
                    {"start": 1.5, "end": 3.5, "text": "오늘 일정을 알려주세요."}
                ]
            }
        }


class TranscriptionRequest(BaseModel):
    """음성 인식 요청 (Base64 인코딩된 오디오)"""
    audio_base64: str = Field(..., description="Base64 인코딩된 오디오 데이터")
    format: str = Field(default="wav", description="오디오 포맷 (wav, mp3)")
    language: Optional[str] = Field(default=None, description="언어 힌트 (없으면 자동 감지)")


class HealthResponse(BaseModel):
    """서비스 상태 응답"""
    status: str = Field(..., description="서비스 상태")
    service: str = Field(..., description="서비스 이름")
    model_loaded: bool = Field(..., description="모델 로드 여부")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "asr",
                "model_loaded": True
            }
        }

