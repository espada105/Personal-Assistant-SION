"""
API Client Module
AWS 백엔드 서비스와 통신하는 클라이언트
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class SionAPIClient:
    """SION 백엔드 API 클라이언트"""
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Args:
            base_url: API 서버 기본 URL
            api_key: API 인증 키
            timeout: 요청 타임아웃 (초)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        
        self._headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
    
    async def transcribe(self, audio_data: bytes) -> str:
        """
        음성을 텍스트로 변환 (ASR)
        
        Args:
            audio_data: WAV 형식의 오디오 바이트
            
        Returns:
            인식된 텍스트
        """
        url = f"{self.base_url}/asr/transcribe"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            files = {"audio": ("audio.wav", audio_data, "audio/wav")}
            headers = {k: v for k, v in self._headers.items() if k != "Content-Type"}
            
            response = await client.post(url, files=files, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            return result.get("text", "")
    
    async def analyze_intent(self, text: str) -> dict:
        """
        텍스트에서 의도와 엔티티 추출 (NLU)
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            의도 및 엔티티 정보
        """
        url = f"{self.base_url}/nlu/analyze"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {"text": text}
            
            response = await client.post(url, json=payload, headers=self._headers)
            response.raise_for_status()
            
            return response.json()
    
    async def execute_task(self, intent: str, entities: dict) -> dict:
        """
        작업 실행 요청
        
        Args:
            intent: 작업 의도
            entities: 추출된 엔티티
            
        Returns:
            작업 실행 결과
        """
        url = f"{self.base_url}/tasks/execute"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "intent": intent,
                "entities": entities
            }
            
            response = await client.post(url, json=payload, headers=self._headers)
            response.raise_for_status()
            
            return response.json()
    
    async def chat(self, message: str, conversation_id: Optional[str] = None) -> dict:
        """
        LLM과 대화
        
        Args:
            message: 사용자 메시지
            conversation_id: 대화 세션 ID (선택)
            
        Returns:
            LLM 응답
        """
        url = f"{self.base_url}/tasks/chat"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "message": message,
                "conversation_id": conversation_id
            }
            
            response = await client.post(url, json=payload, headers=self._headers)
            response.raise_for_status()
            
            return response.json()
    
    async def health_check(self) -> dict:
        """
        서비스 상태 확인
        
        Returns:
            각 서비스의 상태 정보
        """
        results = {}
        services = ["asr", "nlu", "tasks"]
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for service in services:
                try:
                    url = f"{self.base_url}/{service}/health"
                    response = await client.get(url)
                    results[service] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "code": response.status_code
                    }
                except Exception as e:
                    results[service] = {
                        "status": "unreachable",
                        "error": str(e)
                    }
        
        return results


class LocalAPIClient(SionAPIClient):
    """로컬 개발용 API 클라이언트"""
    
    def __init__(self, timeout: float = 30.0):
        super().__init__(
            base_url="http://localhost:8000",
            api_key=None,
            timeout=timeout
        )


class AWSAPIClient(SionAPIClient):
    """AWS 배포 환경용 API 클라이언트"""
    
    def __init__(self, api_key: str, region: str = "ap-northeast-2", timeout: float = 30.0):
        # API Gateway URL 형식
        base_url = f"https://api.sion.{region}.amazonaws.com"
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout
        )


