"""
SION Integration Module
SION 메인앱 통합 모듈

기존 edge-tts를 음성 클로닝 TTS로 대체하기 위한 통합 모듈입니다.
"""

import os
import sys
import logging
import threading
import tempfile
import re
from pathlib import Path
from typing import Optional, Callable

# 로깅 설정
logger = logging.getLogger(__name__)

# 프로젝트 경로
VOICE_DIR = Path(__file__).parent.parent
PROJECT_ROOT = VOICE_DIR.parent


def get_voice_cloning_tts(
    reference_audio: Optional[str] = None,
    reference_text: Optional[str] = None,
    fallback_to_edge: bool = True
):
    """
    음성 클로닝 TTS 인스턴스 반환
    
    SION 메인앱에서 쉽게 사용할 수 있도록 팩토리 함수 제공
    
    Args:
        reference_audio: 참조 음성 파일 경로 (None이면 기본 참조 사용)
        reference_text: 참조 음성 대본
        fallback_to_edge: 음성 클로닝 실패 시 edge-tts 사용 여부
    
    Returns:
        TTS 인스턴스
    
    사용법:
        from voice.app.sion_integration import get_voice_cloning_tts
        tts = get_voice_cloning_tts()
        tts.speak("안녕하세요")
    """
    from .tts_service import SionTTSAdapter
    
    # 기본 참조 음성 경로
    if reference_audio is None:
        default_ref = VOICE_DIR / "reference_audio" / "speaker_1" / "sample.wav"
        if default_ref.exists():
            reference_audio = str(default_ref)
    
    return SionTTSAdapter(
        reference_audio=reference_audio,
        reference_text=reference_text,
        use_fallback=fallback_to_edge
    )


class SionVoiceManager:
    """
    SION 음성 관리자
    
    메인앱의 음성 출력을 관리하는 싱글톤 클래스
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._tts = None
        self._is_speaking = False
        self._voice_mode = True
        self._volume = 1.0
        
        # 콜백
        self._on_speak_start: Optional[Callable] = None
        self._on_speak_end: Optional[Callable] = None
        
        self._initialized = True
        logger.info("SionVoiceManager 초기화 완료")
    
    def initialize(
        self,
        reference_audio: Optional[str] = None,
        reference_text: Optional[str] = None,
        use_voice_cloning: bool = True
    ):
        """
        음성 시스템 초기화
        
        Args:
            reference_audio: 참조 음성 경로
            reference_text: 참조 음성 대본
            use_voice_cloning: 음성 클로닝 사용 여부 (False면 edge-tts만 사용)
        """
        if use_voice_cloning:
            self._tts = get_voice_cloning_tts(
                reference_audio=reference_audio,
                reference_text=reference_text,
                fallback_to_edge=True
            )
        else:
            # edge-tts만 사용
            self._tts = get_voice_cloning_tts(
                reference_audio=None,
                fallback_to_edge=True
            )
        
        logger.info(f"음성 시스템 초기화 완료 (voice_cloning={use_voice_cloning})")
    
    def speak(self, text: str, block: bool = False):
        """
        텍스트 발화
        
        Args:
            text: 발화할 텍스트
            block: 블로킹 여부
        """
        if not self._voice_mode or self._is_speaking:
            return
        
        if self._tts is None:
            self.initialize()
        
        def do_speak():
            self._is_speaking = True
            
            if self._on_speak_start:
                self._on_speak_start()
            
            try:
                # 텍스트 정리
                clean_text = self._clean_text(text)
                
                if clean_text:
                    self._tts.speak(clean_text, block=True)
            
            except Exception as e:
                logger.error(f"발화 오류: {e}")
            
            finally:
                self._is_speaking = False
                if self._on_speak_end:
                    self._on_speak_end()
        
        if block:
            do_speak()
        else:
            thread = threading.Thread(target=do_speak, daemon=True)
            thread.start()
    
    def _clean_text(self, text: str) -> str:
        """텍스트 정리"""
        # 이모지 제거
        text = re.sub(r'[📅📆🕐✅❌🔗💬📧🎤🔴🔊🔇•⚙️]', '', text)
        # 개행을 마침표로
        text = re.sub(r'\n+', '. ', text)
        # 다중 공백 제거
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def stop(self):
        """발화 중지"""
        if self._tts:
            self._tts.stop()
        self._is_speaking = False
    
    def load_voice(
        self,
        audio_path: str,
        reference_text: Optional[str] = None
    ) -> bool:
        """
        새로운 참조 음성 로드
        
        Args:
            audio_path: 참조 음성 경로
            reference_text: 참조 음성 대본
            
        Returns:
            성공 여부
        """
        if self._tts is None:
            self.initialize()
        
        return self._tts.load_voice(audio_path, reference_text)
    
    @property
    def voice_mode(self) -> bool:
        return self._voice_mode
    
    @voice_mode.setter
    def voice_mode(self, value: bool):
        self._voice_mode = value
    
    @property
    def is_speaking(self) -> bool:
        return self._is_speaking
    
    @property
    def is_ready(self) -> bool:
        return self._tts is not None and self._tts.is_ready
    
    def set_callbacks(
        self,
        on_start: Optional[Callable] = None,
        on_end: Optional[Callable] = None
    ):
        """콜백 설정"""
        self._on_speak_start = on_start
        self._on_speak_end = on_end


# 편의 함수
def speak(text: str, block: bool = False):
    """
    간편 발화 함수
    
    사용법:
        from voice.app.sion_integration import speak
        speak("안녕하세요, 시온입니다.")
    """
    manager = SionVoiceManager()
    manager.speak(text, block=block)


def stop_speaking():
    """발화 중지"""
    manager = SionVoiceManager()
    manager.stop()


def set_voice_mode(enabled: bool):
    """음성 모드 설정"""
    manager = SionVoiceManager()
    manager.voice_mode = enabled


# SION main.py용 패치 함수
def patch_sion_tts(app_instance, use_voice_cloning: bool = True):
    """
    SION 앱의 TTS를 음성 클로닝으로 패치
    
    Args:
        app_instance: SionApp 인스턴스
        use_voice_cloning: 음성 클로닝 사용 여부
    
    사용법:
        # main.py의 SionApp.__init__에서
        from voice.app.sion_integration import patch_sion_tts
        patch_sion_tts(self, use_voice_cloning=True)
    """
    manager = SionVoiceManager()
    manager.initialize(use_voice_cloning=use_voice_cloning)
    
    # 원본 speak_text 백업
    original_speak = getattr(app_instance, 'speak_text', None)
    
    def new_speak_text(text: str):
        """패치된 speak_text 함수"""
        if not getattr(app_instance, 'voice_mode', True):
            return
        if getattr(app_instance, 'is_speaking', False):
            return
        
        def do_speak():
            app_instance.is_speaking = True
            try:
                manager.speak(text, block=True)
            finally:
                app_instance.is_speaking = False
        
        threading.Thread(target=do_speak, daemon=True).start()
    
    # 함수 교체
    app_instance.speak_text = new_speak_text
    app_instance._voice_manager = manager
    
    logger.info("SION 앱 TTS 패치 완료")

