"""
Personal Assistant SION - Main Client Entry Point
음성 녹음 및 AWS API 호출을 담당하는 메인 클라이언트
"""

import asyncio
import logging
from pathlib import Path

from audio_recorder import AudioRecorder
from api_client import SionAPIClient
from config import settings

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PersonalAssistant:
    """개인 비서 메인 클래스"""
    
    def __init__(self):
        self.recorder = AudioRecorder()
        self.api_client = SionAPIClient(
            base_url=settings.API_BASE_URL,
            api_key=settings.API_KEY
        )
        self.is_listening = False
    
    async def process_voice_command(self) -> dict:
        """
        음성 명령을 처리하는 메인 파이프라인
        1. 음성 녹음
        2. ASR API 호출 (음성 → 텍스트)
        3. NLU API 호출 (텍스트 → 의도/엔티티)
        4. Task Execution
        """
        try:
            # 1. 음성 녹음
            logger.info("🎤 음성 녹음 시작...")
            audio_data = self.recorder.record()
            logger.info("✅ 음성 녹음 완료")
            
            # 2. ASR: 음성 → 텍스트
            logger.info("🔄 음성 인식 중...")
            transcription = await self.api_client.transcribe(audio_data)
            logger.info(f"📝 인식된 텍스트: {transcription}")
            
            # 3. NLU: 텍스트 → 의도/엔티티
            logger.info("🧠 의도 분석 중...")
            nlu_result = await self.api_client.analyze_intent(transcription)
            logger.info(f"🎯 분석 결과: {nlu_result}")
            
            # 4. Task Execution
            logger.info("⚡ 작업 실행 중...")
            task_result = await self.execute_task(nlu_result)
            logger.info(f"✅ 작업 완료: {task_result}")
            
            return {
                "transcription": transcription,
                "intent": nlu_result,
                "result": task_result
            }
            
        except Exception as e:
            logger.error(f"❌ 오류 발생: {e}")
            raise
    
    async def execute_task(self, nlu_result: dict) -> dict:
        """
        NLU 결과에 따라 적절한 작업 실행
        - 로컬 작업: 파일 탐색, 앱 실행 등
        - 원격 작업: 이메일, 일정, LLM 질의 등
        """
        intent = nlu_result.get("intent", "unknown")
        entities = nlu_result.get("entities", {})
        
        # 로컬에서 처리할 작업
        local_intents = ["file_search", "open_app", "system_control"]
        
        if intent in local_intents:
            return await self._execute_local_task(intent, entities)
        else:
            # AWS에서 처리할 작업
            return await self.api_client.execute_task(intent, entities)
    
    async def _execute_local_task(self, intent: str, entities: dict) -> dict:
        """로컬에서 실행되는 작업"""
        # TODO: 로컬 작업 구현
        logger.info(f"로컬 작업 실행: {intent}")
        return {"status": "success", "message": f"로컬 작업 '{intent}' 실행됨"}
    
    def start(self):
        """비서 시작"""
        logger.info("🚀 Personal Assistant SION 시작")
        logger.info(f"📡 API 서버: {settings.API_BASE_URL}")
        
    def stop(self):
        """비서 종료"""
        logger.info("👋 Personal Assistant SION 종료")


async def main():
    """메인 함수"""
    assistant = PersonalAssistant()
    assistant.start()
    
    try:
        # 예시: 단일 음성 명령 처리
        result = await assistant.process_voice_command()
        print(f"결과: {result}")
    except KeyboardInterrupt:
        pass
    finally:
        assistant.stop()


if __name__ == "__main__":
    asyncio.run(main())


