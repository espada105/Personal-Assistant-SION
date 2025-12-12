"""
LLM Task Handler
OpenAI API를 사용한 LLM 대화 및 질의응답
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from .base_task import BaseTask

logger = logging.getLogger(__name__)


class LLMTask(BaseTask):
    """LLM 작업 핸들러"""
    
    # 시스템 프롬프트
    SYSTEM_PROMPT = """당신은 SION이라는 이름의 유능한 개인 비서 AI입니다.
사용자의 요청에 친절하고 정확하게 응답해주세요.
한국어로 대화하며, 필요한 경우 영어 용어도 사용할 수 있습니다.

주요 역할:
- 일정 관리 도움
- 이메일 관련 질문 답변
- 일반적인 질문에 대한 답변
- 정보 검색 및 요약

응답 시 주의사항:
- 간결하고 명확하게 답변
- 필요시 단계별로 설명
- 불확실한 정보는 명시
"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        max_tokens: int = 1000
    ):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.client = None
        
        # 대화 히스토리 저장 (conversation_id -> messages)
        self.conversations: Dict[str, List[Dict]] = {}
        
        self._init_client()
    
    def _init_client(self):
        """OpenAI 클라이언트 초기화"""
        if not self.api_key:
            logger.warning("OpenAI API 키가 설정되지 않았습니다.")
            return
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI 클라이언트 초기화 완료")
        except Exception as e:
            logger.error(f"OpenAI 클라이언트 초기화 실패: {e}")
    
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLM 작업 실행
        
        Actions:
            - chat: 일반 대화
            - search: 웹 검색 시뮬레이션
            - weather: 날씨 정보 (더미)
            - summarize: 텍스트 요약
        """
        if action == "chat":
            return await self._chat(params)
        elif action == "search":
            return await self._search(params)
        elif action == "weather":
            return await self._weather(params)
        elif action == "summarize":
            return await self._summarize(params)
        else:
            raise ValueError(f"지원하지 않는 액션: {action}")
    
    async def _chat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """일반 대화"""
        message = params.get("message", "")
        conversation_id = params.get("conversation_id")
        
        if not message:
            return {
                "response": "메시지를 입력해주세요.",
                "conversation_id": None,
                "tokens_used": 0
            }
        
        # 대화 세션 관리
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            self.conversations[conversation_id] = []
        
        # 대화 히스토리 가져오기
        history = self.conversations.get(conversation_id, [])
        
        # 메시지 구성
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        messages.extend(history)
        messages.append({"role": "user", "content": message})
        
        # API가 없으면 더미 응답
        if not self.client:
            dummy_response = f"안녕하세요! SION입니다. '{message}'에 대한 답변을 드리고 싶지만, 현재 LLM 서비스가 설정되지 않았습니다."
            
            return {
                "response": dummy_response,
                "conversation_id": conversation_id,
                "tokens_used": 0
            }
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            
            assistant_message = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            # 히스토리 업데이트
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": assistant_message})
            
            # 히스토리 제한 (최근 10개 메시지만 유지)
            if len(history) > 20:
                history = history[-20:]
            
            self.conversations[conversation_id] = history
            
            return {
                "response": assistant_message,
                "conversation_id": conversation_id,
                "tokens_used": tokens_used
            }
            
        except Exception as e:
            logger.error(f"LLM 대화 오류: {e}")
            return {
                "response": f"죄송합니다, 응답 생성 중 오류가 발생했습니다: {str(e)}",
                "conversation_id": conversation_id,
                "tokens_used": 0
            }
    
    async def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """웹 검색 시뮬레이션 (LLM 지식 기반)"""
        query = params.get("query", params.get("message", ""))
        
        search_prompt = f"""사용자가 다음을 검색하고 있습니다: "{query}"

이에 대해 알고 있는 정보를 바탕으로 유용한 답변을 제공해주세요.
정확하지 않을 수 있는 정보는 그렇다고 명시해주세요."""
        
        return await self._chat({"message": search_prompt, **params})
    
    async def _weather(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """날씨 정보 (더미)"""
        location = params.get("location", "서울")
        
        # 실제로는 날씨 API를 호출해야 함
        return {
            "response": f"{location}의 현재 날씨 정보입니다:\n"
                       f"- 온도: 15°C\n"
                       f"- 날씨: 맑음\n"
                       f"- 습도: 45%\n"
                       f"(참고: 이것은 더미 데이터입니다. 실제 날씨 API 연동이 필요합니다.)",
            "conversation_id": None,
            "tokens_used": 0
        }
    
    async def _summarize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """텍스트 요약"""
        text = params.get("text", "")
        
        if not text:
            return {
                "response": "요약할 텍스트를 입력해주세요.",
                "conversation_id": None,
                "tokens_used": 0
            }
        
        summarize_prompt = f"""다음 텍스트를 간결하게 요약해주세요:

{text}

핵심 포인트를 bullet point로 정리해주세요."""
        
        return await self._chat({"message": summarize_prompt, **params})
    
    def clear_conversation(self, conversation_id: str):
        """대화 히스토리 삭제"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]


