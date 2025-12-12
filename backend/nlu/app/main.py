"""
NLU Service - FastAPI Application
텍스트에서 의도와 엔티티를 추출하는 REST API
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .intent_classifier import IntentClassifier
from .schemas import (
    NLURequest,
    NLUResponse,
    HealthResponse,
    IntentInfo,
    EntityInfo
)

# 로깅 설정
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 전역 모델 인스턴스
nlu_model: IntentClassifier = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명 주기 관리"""
    global nlu_model
    
    # 시작 시 모델 로드
    logger.info("NLU 모델 로딩 중...")
    model_path = os.getenv("MODEL_PATH", "./models")
    
    nlu_model = IntentClassifier(model_path=model_path)
    nlu_model.load()
    logger.info("NLU 모델 로드 완료")
    
    yield
    
    # 종료 시 정리
    logger.info("NLU 서비스 종료")


app = FastAPI(
    title="SION NLU Service",
    description="의도 분류 및 엔티티 추출 API",
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
        service="nlu",
        model_loaded=nlu_model is not None and nlu_model.is_loaded
    )


@app.post("/analyze", response_model=NLUResponse)
async def analyze_text(request: NLURequest):
    """
    텍스트에서 의도와 엔티티 추출
    
    - **text**: 분석할 텍스트
    
    Returns:
        의도(Intent) 및 엔티티(Entities) 정보
    """
    if nlu_model is None or not nlu_model.is_loaded:
        raise HTTPException(status_code=503, detail="NLU 모델이 로드되지 않았습니다.")
    
    try:
        result = nlu_model.analyze(request.text)
        
        return NLUResponse(
            text=request.text,
            intent=IntentInfo(
                name=result["intent"],
                confidence=result["intent_confidence"]
            ),
            entities=[
                EntityInfo(
                    type=entity["type"],
                    value=entity["value"],
                    start=entity.get("start", 0),
                    end=entity.get("end", 0)
                )
                for entity in result.get("entities", [])
            ]
        )
        
    except Exception as e:
        logger.error(f"NLU 분석 오류: {e}")
        raise HTTPException(status_code=500, detail=f"텍스트 분석 중 오류 발생: {str(e)}")


@app.post("/classify")
async def classify_intent(request: NLURequest):
    """
    의도만 분류 (엔티티 추출 없음, 더 빠름)
    """
    if nlu_model is None or not nlu_model.is_loaded:
        raise HTTPException(status_code=503, detail="NLU 모델이 로드되지 않았습니다.")
    
    try:
        intent, confidence = nlu_model.classify_intent(request.text)
        
        return {
            "text": request.text,
            "intent": intent,
            "confidence": confidence
        }
        
    except Exception as e:
        logger.error(f"의도 분류 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/intents")
async def list_intents():
    """
    지원하는 의도 목록 조회
    """
    if nlu_model is None:
        raise HTTPException(status_code=503, detail="NLU 모델이 로드되지 않았습니다.")
    
    return {
        "intents": nlu_model.get_supported_intents()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


