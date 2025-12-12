"""
ASR Service - FastAPI Application
음성을 텍스트로 변환하는 REST API
"""

import logging
import os
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .model import ASRModel
from .schemas import TranscriptionResponse, HealthResponse

# 로깅 설정
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 전역 모델 인스턴스
asr_model: ASRModel = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명 주기 관리"""
    global asr_model
    
    # 시작 시 모델 로드
    logger.info("ASR 모델 로딩 중...")
    model_path = os.getenv("MODEL_PATH", "./models")
    model_name = os.getenv("ASR_MODEL_NAME", "base")
    
    asr_model = ASRModel(model_name=model_name, model_path=model_path)
    asr_model.load()
    logger.info("ASR 모델 로드 완료")
    
    yield
    
    # 종료 시 정리
    logger.info("ASR 서비스 종료")


app = FastAPI(
    title="SION ASR Service",
    description="Whisper 기반 음성 인식 API",
    version="0.1.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """서비스 상태 확인"""
    return HealthResponse(
        status="healthy",
        service="asr",
        model_loaded=asr_model is not None and asr_model.is_loaded
    )


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="WAV 형식의 오디오 파일")
):
    """
    음성 파일을 텍스트로 변환
    
    - **audio**: WAV 형식의 오디오 파일 (16kHz, 모노 권장)
    
    Returns:
        인식된 텍스트 및 메타데이터
    """
    if asr_model is None or not asr_model.is_loaded:
        raise HTTPException(status_code=503, detail="ASR 모델이 로드되지 않았습니다.")
    
    # 지원 형식 확인
    allowed_types = ["audio/wav", "audio/wave", "audio/x-wav", "audio/mpeg", "audio/mp3"]
    if audio.content_type and audio.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"지원하지 않는 오디오 형식입니다. 지원 형식: {allowed_types}"
        )
    
    try:
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            content = await audio.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        # 음성 인식 수행
        result = asr_model.transcribe(tmp_path)
        
        # 임시 파일 삭제
        os.unlink(tmp_path)
        
        return TranscriptionResponse(
            text=result["text"],
            language=result.get("language", "ko"),
            duration=result.get("duration", 0.0),
            confidence=result.get("confidence", 1.0)
        )
        
    except Exception as e:
        logger.error(f"음성 인식 오류: {e}")
        raise HTTPException(status_code=500, detail=f"음성 인식 중 오류 발생: {str(e)}")


@app.post("/transcribe/stream")
async def transcribe_stream(
    audio: UploadFile = File(...)
):
    """
    스트리밍 음성 인식 (실시간)
    
    TODO: WebSocket 기반 실시간 스트리밍 구현
    """
    raise HTTPException(status_code=501, detail="스트리밍 기능은 아직 구현되지 않았습니다.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


