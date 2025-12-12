"""
Task Executor Service - FastAPI Application
의도에 따라 적절한 작업을 실행하는 REST API
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    TaskRequest,
    TaskResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse
)
from .tasks.email_task import EmailTask
from .tasks.calendar_task import CalendarTask
from .tasks.llm_task import LLMTask

# 로깅 설정
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 전역 태스크 핸들러
task_handlers = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명 주기 관리"""
    global task_handlers
    
    # 시작 시 태스크 핸들러 초기화
    logger.info("Task Executor 초기화 중...")
    
    # 이메일 태스크
    task_handlers["email"] = EmailTask(
        credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH")
    )
    
    # 캘린더 태스크
    task_handlers["calendar"] = CalendarTask(
        credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH")
    )
    
    # LLM 태스크
    task_handlers["llm"] = LLMTask(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    )
    
    logger.info("Task Executor 초기화 완료")
    
    yield
    
    # 종료 시 정리
    logger.info("Task Executor 종료")


app = FastAPI(
    title="SION Task Executor Service",
    description="의도 기반 작업 실행 API",
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


# 의도-작업 매핑
INTENT_TASK_MAP = {
    "schedule_check": ("calendar", "check"),
    "schedule_add": ("calendar", "add"),
    "schedule_delete": ("calendar", "delete"),
    "email_check": ("email", "check"),
    "email_send": ("email", "send"),
    "llm_chat": ("llm", "chat"),
    "web_search": ("llm", "search"),
    "weather_check": ("llm", "weather"),
}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """서비스 상태 확인"""
    return HealthResponse(
        status="healthy",
        service="task_executor",
        handlers_loaded=list(task_handlers.keys())
    )


@app.post("/execute", response_model=TaskResponse)
async def execute_task(request: TaskRequest):
    """
    의도에 따른 작업 실행
    
    - **intent**: 실행할 작업 의도
    - **entities**: 추출된 엔티티 (작업 파라미터)
    
    Returns:
        작업 실행 결과
    """
    intent = request.intent
    entities = request.entities or {}
    
    logger.info(f"작업 실행 요청: intent={intent}, entities={entities}")
    
    # 의도에 해당하는 태스크 찾기
    task_info = INTENT_TASK_MAP.get(intent)
    
    if not task_info:
        # 알 수 없는 의도는 LLM에게 전달
        task_info = ("llm", "chat")
        entities["query"] = f"사용자 의도: {intent}"
    
    handler_name, action = task_info
    handler = task_handlers.get(handler_name)
    
    if not handler:
        raise HTTPException(
            status_code=500,
            detail=f"태스크 핸들러를 찾을 수 없습니다: {handler_name}"
        )
    
    try:
        result = await handler.execute(action, entities)
        
        return TaskResponse(
            success=True,
            intent=intent,
            action=action,
            result=result,
            message="작업이 성공적으로 완료되었습니다."
        )
        
    except Exception as e:
        logger.error(f"작업 실행 오류: {e}")
        return TaskResponse(
            success=False,
            intent=intent,
            action=action,
            result=None,
            message=f"작업 실행 중 오류가 발생했습니다: {str(e)}"
        )


@app.post("/chat", response_model=ChatResponse)
async def chat_with_llm(request: ChatRequest):
    """
    LLM과 대화
    
    - **message**: 사용자 메시지
    - **conversation_id**: 대화 세션 ID (선택)
    
    Returns:
        LLM 응답
    """
    llm_handler = task_handlers.get("llm")
    
    if not llm_handler:
        raise HTTPException(status_code=503, detail="LLM 서비스를 사용할 수 없습니다.")
    
    try:
        result = await llm_handler.execute("chat", {
            "message": request.message,
            "conversation_id": request.conversation_id
        })
        
        return ChatResponse(
            message=result.get("response", ""),
            conversation_id=result.get("conversation_id"),
            tokens_used=result.get("tokens_used", 0)
        )
        
    except Exception as e:
        logger.error(f"LLM 대화 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks")
async def list_tasks():
    """
    지원하는 작업 목록 조회
    """
    return {
        "tasks": list(INTENT_TASK_MAP.keys()),
        "handlers": list(task_handlers.keys())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


