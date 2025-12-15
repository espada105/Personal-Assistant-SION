"""
Voice Cloning API Server
음성 클로닝 API 서버

FastAPI 기반 REST API를 제공합니다.

사용법:
    uvicorn api_server:app --host 0.0.0.0 --port 9880
"""

import os
import sys
import logging
import tempfile
import asyncio
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
import base64
import io

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

# 상위 디렉토리 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tts_service import VoiceCloningTTS
from app.audio_utils import AudioProcessor

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 전역 TTS 인스턴스
_tts_service: Optional[VoiceCloningTTS] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""
    global _tts_service
    
    # 시작 시 TTS 서비스 초기화
    logger.info("TTS 서비스 초기화 중...")
    _tts_service = VoiceCloningTTS()
    
    # 기본 참조 음성이 있으면 로드
    default_ref = Path(__file__).parent.parent / "reference_audio" / "speaker_1" / "sample.wav"
    if default_ref.exists():
        _tts_service.initialize()
        _tts_service.load_voice(default_ref)
        logger.info(f"기본 참조 음성 로드: {default_ref}")
    
    yield
    
    # 종료 시 정리
    if _tts_service:
        _tts_service.cleanup()
    logger.info("TTS 서비스 종료")


# FastAPI 앱 생성
app = FastAPI(
    title="SION Voice Cloning API",
    description="일본 성우 음성으로 한국어를 발화하는 교차언어 음성 클로닝 API",
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


# ===== Pydantic Models =====

class SynthesizeRequest(BaseModel):
    """음성 합성 요청"""
    text: str = Field(..., description="합성할 텍스트", min_length=1)
    speed: float = Field(1.0, ge=0.5, le=2.0, description="재생 속도")
    pitch_shift: float = Field(0.0, ge=-12, le=12, description="피치 시프트 (반음)")
    format: str = Field("wav", description="출력 포맷 (wav, mp3)")


class SynthesizeResponse(BaseModel):
    """음성 합성 응답"""
    success: bool
    message: str
    audio_base64: Optional[str] = None
    duration: Optional[float] = None


class LoadVoiceRequest(BaseModel):
    """음성 로드 요청"""
    reference_text: Optional[str] = Field(None, description="참조 음성 대본")
    language: str = Field("ja", description="참조 음성 언어")


class StatusResponse(BaseModel):
    """상태 응답"""
    status: str
    is_ready: bool
    speaker_info: Optional[dict] = None


# ===== API Endpoints =====

@app.get("/", tags=["Info"])
async def root():
    """API 정보"""
    return {
        "name": "SION Voice Cloning API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/status", response_model=StatusResponse, tags=["Status"])
async def get_status():
    """TTS 서비스 상태 확인"""
    global _tts_service
    
    if _tts_service is None:
        return StatusResponse(
            status="not_initialized",
            is_ready=False
        )
    
    return StatusResponse(
        status="ready" if _tts_service.is_ready else "no_voice_loaded",
        is_ready=_tts_service.is_ready,
        speaker_info=_tts_service.get_voice_info()
    )


@app.post("/load_voice", tags=["Voice"])
async def load_voice(
    audio_file: UploadFile = File(..., description="참조 음성 파일 (WAV)"),
    reference_text: Optional[str] = Form(None, description="참조 음성 대본"),
    language: str = Form("ja", description="참조 음성 언어")
):
    """
    참조 음성 로드
    
    음성 클로닝을 위한 참조 음성을 업로드합니다.
    """
    global _tts_service
    
    if _tts_service is None:
        _tts_service = VoiceCloningTTS()
    
    _tts_service.initialize()
    
    # 임시 파일로 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        content = await audio_file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        success = _tts_service.load_voice(
            audio_path=tmp_path,
            reference_text=reference_text,
            language=language
        )
        
        if success:
            return {"success": True, "message": "참조 음성 로드 완료"}
        else:
            raise HTTPException(status_code=400, detail="참조 음성 로드 실패")
    
    finally:
        # 임시 파일 삭제
        try:
            os.remove(tmp_path)
        except:
            pass


@app.post("/synthesize", response_model=SynthesizeResponse, tags=["Synthesis"])
async def synthesize(request: SynthesizeRequest):
    """
    텍스트를 음성으로 합성
    
    한국어 텍스트를 일본 성우 음성으로 합성합니다.
    """
    global _tts_service
    
    if _tts_service is None or not _tts_service.is_ready:
        raise HTTPException(
            status_code=400,
            detail="음성이 로드되지 않았습니다. /load_voice 엔드포인트를 먼저 호출하세요."
        )
    
    try:
        # 음성 합성
        audio = _tts_service.synthesize(
            text=request.text,
            speed=request.speed,
            pitch_shift=request.pitch_shift
        )
        
        # 오디오를 base64로 인코딩
        import soundfile as sf
        buffer = io.BytesIO()
        sf.write(buffer, audio, 44100, format='WAV')
        buffer.seek(0)
        audio_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        duration = len(audio) / 44100
        
        return SynthesizeResponse(
            success=True,
            message="합성 완료",
            audio_base64=audio_base64,
            duration=duration
        )
    
    except Exception as e:
        logger.error(f"합성 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/synthesize_file", tags=["Synthesis"])
async def synthesize_file(
    text: str = Form(..., description="합성할 텍스트"),
    speed: float = Form(1.0, ge=0.5, le=2.0, description="재생 속도"),
    pitch_shift: float = Form(0.0, ge=-12, le=12, description="피치 시프트"),
    background_tasks: BackgroundTasks = None
):
    """
    텍스트를 음성 파일로 합성
    
    합성된 음성을 WAV 파일로 반환합니다.
    """
    global _tts_service
    
    if _tts_service is None or not _tts_service.is_ready:
        raise HTTPException(
            status_code=400,
            detail="음성이 로드되지 않았습니다."
        )
    
    try:
        # 음성 합성
        audio = _tts_service.synthesize(
            text=text,
            speed=speed,
            pitch_shift=pitch_shift
        )
        
        # 임시 파일 생성
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        import soundfile as sf
        sf.write(tmp.name, audio, 44100)
        tmp.close()
        
        # 백그라운드에서 파일 삭제
        def cleanup():
            try:
                os.remove(tmp.name)
            except:
                pass
        
        if background_tasks:
            background_tasks.add_task(cleanup)
        
        return FileResponse(
            tmp.name,
            media_type="audio/wav",
            filename="synthesized.wav"
        )
    
    except Exception as e:
        logger.error(f"합성 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/synthesize_stream", tags=["Synthesis"])
async def synthesize_stream(request: SynthesizeRequest):
    """
    스트리밍 음성 합성
    
    합성된 음성을 청크 단위로 스트리밍합니다.
    """
    global _tts_service
    
    if _tts_service is None or not _tts_service.is_ready:
        raise HTTPException(
            status_code=400,
            detail="음성이 로드되지 않았습니다."
        )
    
    async def audio_generator():
        """오디오 청크 생성기"""
        try:
            audio = _tts_service.synthesize(
                text=request.text,
                speed=request.speed,
                pitch_shift=request.pitch_shift
            )
            
            import soundfile as sf
            buffer = io.BytesIO()
            sf.write(buffer, audio, 44100, format='WAV')
            buffer.seek(0)
            
            # 청크 단위로 반환
            chunk_size = 4096
            while True:
                chunk = buffer.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        
        except Exception as e:
            logger.error(f"스트리밍 오류: {e}")
            raise
    
    return StreamingResponse(
        audio_generator(),
        media_type="audio/wav"
    )


@app.get("/voices", tags=["Voice"])
async def list_voices():
    """
    사용 가능한 참조 음성 목록
    """
    reference_dir = Path(__file__).parent.parent / "reference_audio"
    
    voices = []
    if reference_dir.exists():
        for speaker_dir in reference_dir.iterdir():
            if speaker_dir.is_dir():
                audio_files = list(speaker_dir.glob("*.wav"))
                if audio_files:
                    voices.append({
                        "speaker_id": speaker_dir.name,
                        "files": [f.name for f in audio_files]
                    })
    
    return {"voices": voices}


@app.post("/settings", tags=["Settings"])
async def update_settings(
    speed: Optional[float] = Form(None, ge=0.5, le=2.0),
    pitch_shift: Optional[float] = Form(None, ge=-12, le=12),
    volume: Optional[float] = Form(None, ge=0.0, le=2.0)
):
    """
    TTS 설정 업데이트
    """
    global _tts_service
    
    if _tts_service is None:
        raise HTTPException(status_code=400, detail="TTS 서비스가 초기화되지 않았습니다.")
    
    if speed is not None:
        _tts_service.speed = speed
    if pitch_shift is not None:
        _tts_service.pitch_shift = pitch_shift
    if volume is not None:
        _tts_service.volume = volume
    
    return {
        "success": True,
        "settings": {
            "speed": _tts_service.speed,
            "pitch_shift": _tts_service.pitch_shift,
            "volume": _tts_service.volume
        }
    }


# 메인 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host="127.0.0.1",
        port=9880,
        reload=True
    )

