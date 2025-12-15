"""
Voice Cloning TTS Service
SION 프로젝트용 음성 클로닝 TTS 서비스

기존 edge-tts를 대체하여 일본 성우 음성으로 한국어를 발화합니다.
"""

import os
import sys
import logging
import tempfile
import threading
import asyncio
from pathlib import Path
from typing import Optional, Union, Dict, Any, Callable
import numpy as np

# 모듈 경로 추가
VOICE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(VOICE_DIR))

from .voice_cloner import VoiceCloner
from .audio_utils import AudioProcessor, AudioPlayer

# 로깅 설정
logger = logging.getLogger(__name__)


class VoiceCloningTTS:
    """
    음성 클로닝 기반 TTS 서비스
    
    SION 프로젝트의 edge-tts를 대체하여 사용합니다.
    일본 성우의 목소리로 한국어 텍스트를 발화합니다.
    
    사용법:
        tts = VoiceCloningTTS()
        tts.load_voice("path/to/reference.wav", "こんにちは")
        tts.speak("안녕하세요, 시온입니다.")
    """
    
    def __init__(
        self,
        reference_audio: Optional[str] = None,
        reference_text: Optional[str] = None,
        config_path: Optional[str] = None,
        device: str = "cuda",
        auto_initialize: bool = False
    ):
        """
        Args:
            reference_audio: 참조 음성 파일 경로
            reference_text: 참조 음성의 대본 (일본어)
            config_path: 설정 파일 경로
            device: 사용할 디바이스 (cuda, cpu, mps)
            auto_initialize: True면 즉시 모델 초기화
        """
        self.config_path = config_path or str(VOICE_DIR / "config.yaml")
        self.device = device
        
        # 컴포넌트 초기화
        self._cloner: Optional[VoiceCloner] = None
        self._audio_processor = AudioProcessor()
        self._player = AudioPlayer()
        
        # 상태
        self._is_speaking = False
        self._speaking_thread: Optional[threading.Thread] = None
        
        # 설정
        self._speed = 1.0
        self._pitch_shift = 0.0
        self._volume = 1.0
        
        # 콜백
        self._on_speak_start: Optional[Callable] = None
        self._on_speak_end: Optional[Callable] = None
        
        # 초기화
        if auto_initialize:
            self.initialize()
            if reference_audio:
                self.load_voice(reference_audio, reference_text)
        
        logger.info("VoiceCloningTTS 서비스 초기화 완료")
    
    def initialize(self):
        """모델 초기화"""
        if self._cloner is None:
            self._cloner = VoiceCloner(
                config_path=self.config_path,
                device=self.device
            )
            self._cloner.initialize()
    
    def load_voice(
        self,
        audio_path: Union[str, Path],
        reference_text: Optional[str] = None,
        language: str = "ja"
    ) -> bool:
        """
        음성 클로닝을 위한 참조 음성 로드
        
        Args:
            audio_path: 참조 음성 파일 경로 (WAV 권장)
            reference_text: 참조 음성의 대본 (품질 향상에 도움)
            language: 참조 음성의 언어 (기본: 일본어)
            
        Returns:
            성공 여부
        """
        if self._cloner is None:
            self.initialize()
        
        return self._cloner.load_reference_audio(
            audio_path=audio_path,
            reference_text=reference_text,
            language=language
        )
    
    def synthesize(
        self,
        text: str,
        speed: Optional[float] = None,
        pitch_shift: Optional[float] = None
    ) -> np.ndarray:
        """
        텍스트를 음성으로 변환
        
        Args:
            text: 한국어 텍스트
            speed: 재생 속도 (None이면 기본값 사용)
            pitch_shift: 피치 시프트 (None이면 기본값 사용)
            
        Returns:
            음성 데이터 (numpy array)
        """
        if self._cloner is None or not self._cloner.is_ready:
            raise RuntimeError("음성 클로닝이 준비되지 않았습니다. load_voice()를 먼저 호출하세요.")
        
        # 파라미터 설정
        speed = speed if speed is not None else self._speed
        pitch_shift = pitch_shift if pitch_shift is not None else self._pitch_shift
        
        # 음성 합성
        audio, sample_rate = self._cloner.synthesize(
            text=text,
            language="ko",
            speed=speed,
            pitch_shift=pitch_shift
        )
        
        # 볼륨 조정
        if self._volume != 1.0:
            audio = audio * self._volume
        
        # 페이드 인/아웃 추가
        audio = self._audio_processor.add_fade(
            audio, sample_rate,
            fade_in_ms=10,
            fade_out_ms=10
        )
        
        return audio
    
    def speak(
        self,
        text: str,
        block: bool = True,
        speed: Optional[float] = None,
        pitch_shift: Optional[float] = None
    ):
        """
        텍스트를 음성으로 발화
        
        Args:
            text: 발화할 텍스트
            block: True면 발화 완료까지 대기
            speed: 재생 속도
            pitch_shift: 피치 시프트
        """
        if self._is_speaking:
            self.stop()
        
        def _speak():
            self._is_speaking = True
            
            if self._on_speak_start:
                self._on_speak_start()
            
            try:
                audio = self.synthesize(text, speed, pitch_shift)
                self._player.play(audio, sample_rate=44100, block=True)
            except Exception as e:
                logger.error(f"발화 오류: {e}")
            finally:
                self._is_speaking = False
                if self._on_speak_end:
                    self._on_speak_end()
        
        if block:
            _speak()
        else:
            self._speaking_thread = threading.Thread(target=_speak, daemon=True)
            self._speaking_thread.start()
    
    def speak_async(
        self,
        text: str,
        speed: Optional[float] = None,
        pitch_shift: Optional[float] = None
    ):
        """비동기 발화 (블로킹 없음)"""
        self.speak(text, block=False, speed=speed, pitch_shift=pitch_shift)
    
    def save(
        self,
        text: str,
        output_path: Union[str, Path],
        speed: Optional[float] = None,
        pitch_shift: Optional[float] = None
    ):
        """
        텍스트를 음성 파일로 저장
        
        Args:
            text: 발화할 텍스트
            output_path: 저장 경로
            speed: 재생 속도
            pitch_shift: 피치 시프트
        """
        audio = self.synthesize(text, speed, pitch_shift)
        self._audio_processor.save_audio(audio, output_path, sample_rate=44100)
        logger.info(f"음성 파일 저장 완료: {output_path}")
    
    def stop(self):
        """발화 중지"""
        self._player.stop()
        self._is_speaking = False
    
    def pause(self):
        """발화 일시정지"""
        self._player.pause()
    
    def resume(self):
        """발화 재개"""
        self._player.resume()
    
    # 속성 설정
    @property
    def speed(self) -> float:
        return self._speed
    
    @speed.setter
    def speed(self, value: float):
        self._speed = max(0.5, min(2.0, value))
    
    @property
    def pitch_shift(self) -> float:
        return self._pitch_shift
    
    @pitch_shift.setter
    def pitch_shift(self, value: float):
        self._pitch_shift = max(-12, min(12, value))
    
    @property
    def volume(self) -> float:
        return self._volume
    
    @volume.setter
    def volume(self, value: float):
        self._volume = max(0.0, min(2.0, value))
        self._player.set_volume(value)
    
    @property
    def is_speaking(self) -> bool:
        return self._is_speaking
    
    @property
    def is_ready(self) -> bool:
        return self._cloner is not None and self._cloner.is_ready
    
    # 콜백 설정
    def set_on_speak_start(self, callback: Callable):
        """발화 시작 콜백 설정"""
        self._on_speak_start = callback
    
    def set_on_speak_end(self, callback: Callable):
        """발화 종료 콜백 설정"""
        self._on_speak_end = callback
    
    def get_voice_info(self) -> Optional[Dict[str, Any]]:
        """현재 로드된 음성 정보 반환"""
        if self._cloner:
            return self._cloner.get_speaker_info()
        return None
    
    def cleanup(self):
        """리소스 정리"""
        self.stop()
        if self._cloner:
            self._cloner.unload()
        logger.info("VoiceCloningTTS 리소스 정리 완료")


# SION 프로젝트 호환 래퍼
class SionTTSAdapter:
    """
    SION 프로젝트 메인 앱과 호환되는 TTS 어댑터
    
    기존 edge-tts 코드와 동일한 인터페이스를 제공합니다.
    """
    
    def __init__(
        self,
        reference_audio: Optional[str] = None,
        reference_text: Optional[str] = None,
        use_fallback: bool = True
    ):
        """
        Args:
            reference_audio: 참조 음성 파일 경로
            reference_text: 참조 음성 대본
            use_fallback: 음성 클로닝 실패 시 edge-tts 사용 여부
        """
        self.use_fallback = use_fallback
        self._tts: Optional[VoiceCloningTTS] = None
        self._fallback_available = False
        
        # 음성 클로닝 TTS 초기화 시도
        try:
            self._tts = VoiceCloningTTS(auto_initialize=False)
            if reference_audio:
                self._tts.initialize()
                self._tts.load_voice(reference_audio, reference_text)
        except Exception as e:
            logger.warning(f"음성 클로닝 TTS 초기화 실패: {e}")
        
        # Fallback edge-tts 확인
        try:
            import edge_tts
            self._fallback_available = True
        except ImportError:
            pass
    
    async def speak_async_edge(self, text: str, voice: str = "ko-KR-SunHiNeural"):
        """edge-tts를 사용한 비동기 발화 (fallback)"""
        import edge_tts
        import tempfile
        import pygame
        
        communicate = edge_tts.Communicate(text, voice)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp_path = tmp.name
        
        await communicate.save(tmp_path)
        
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
        
        try:
            os.remove(tmp_path)
        except:
            pass
    
    def speak(self, text: str, block: bool = True):
        """
        텍스트 발화 (SION 호환 인터페이스)
        
        Args:
            text: 발화할 텍스트
            block: 블로킹 여부
        """
        # 음성 클로닝 TTS 시도
        if self._tts and self._tts.is_ready:
            try:
                self._tts.speak(text, block=block)
                return
            except Exception as e:
                logger.warning(f"음성 클로닝 발화 실패: {e}")
        
        # Fallback to edge-tts
        if self.use_fallback and self._fallback_available:
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.speak_async_edge(text))
                loop.close()
            except Exception as e:
                logger.error(f"Fallback 발화도 실패: {e}")
    
    def load_voice(self, audio_path: str, reference_text: Optional[str] = None) -> bool:
        """참조 음성 로드"""
        if self._tts is None:
            self._tts = VoiceCloningTTS()
        
        self._tts.initialize()
        return self._tts.load_voice(audio_path, reference_text)
    
    def stop(self):
        """발화 중지"""
        if self._tts:
            self._tts.stop()
    
    @property
    def is_ready(self) -> bool:
        """사용 가능 여부"""
        if self._tts and self._tts.is_ready:
            return True
        return self._fallback_available

