"""
Voice Cloner
GPT-SoVITS 기반 음성 클로닝 래퍼
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union, Tuple
import numpy as np
import yaml

# 로깅 설정
logger = logging.getLogger(__name__)


class VoiceCloner:
    """
    GPT-SoVITS 기반 음성 클로닝 클래스
    
    교차언어 음성 클로닝을 지원하며, 일본어 참조 음성으로
    한국어 텍스트를 자연스럽게 발화합니다.
    """
    
    # 지원 언어 코드
    SUPPORTED_LANGUAGES = {
        "ko": "한국어",
        "ja": "日本語",
        "en": "English",
        "zh": "中文"
    }
    
    def __init__(
        self,
        gpt_model_path: Optional[str] = None,
        sovits_model_path: Optional[str] = None,
        config_path: Optional[str] = None,
        device: str = "cuda"
    ):
        """
        Args:
            gpt_model_path: GPT 모델 경로
            sovits_model_path: SoVITS 모델 경로
            config_path: 설정 파일 경로
            device: 사용할 디바이스 (cuda, cpu, mps)
        """
        self.device = device
        self.config = self._load_config(config_path)
        
        # 모델 경로 설정
        self.gpt_model_path = gpt_model_path or self.config.get("model", {}).get("gpt", {}).get("pretrained_path")
        self.sovits_model_path = sovits_model_path or self.config.get("model", {}).get("sovits", {}).get("pretrained_path")
        
        # 모델 인스턴스 (lazy loading)
        self._gpt_model = None
        self._sovits_model = None
        self._is_initialized = False
        
        # 현재 로드된 참조 음성 정보
        self._current_reference = None
        
        logger.info(f"VoiceCloner 초기화 완료 (device: {device})")
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """설정 파일 로드"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        if Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        
        return {}
    
    def initialize(self):
        """모델 초기화 및 로드"""
        if self._is_initialized:
            return
        
        try:
            self._load_models()
            self._is_initialized = True
            logger.info("모델 초기화 완료")
        except Exception as e:
            logger.error(f"모델 초기화 실패: {e}")
            raise
    
    def _load_models(self):
        """
        GPT-SoVITS 모델 로드
        
        실제 GPT-SoVITS 라이브러리가 설치되어 있어야 합니다.
        """
        try:
            # GPT-SoVITS 라이브러리 임포트 시도
            # 실제 설치 시 아래 코드가 활성화됩니다
            
            # from GPT_SoVITS.inference import TTS
            # self._tts_engine = TTS(
            #     gpt_path=self.gpt_model_path,
            #     sovits_path=self.sovits_model_path,
            #     device=self.device
            # )
            
            # 개발/테스트용 더미 초기화
            logger.warning("GPT-SoVITS 라이브러리가 설치되지 않았습니다. 더미 모드로 실행합니다.")
            self._tts_engine = None
            
        except ImportError as e:
            logger.warning(f"GPT-SoVITS 임포트 실패: {e}")
            self._tts_engine = None
    
    def load_reference_audio(
        self,
        audio_path: Union[str, Path],
        reference_text: Optional[str] = None,
        language: str = "ja"
    ) -> bool:
        """
        참조 음성 로드
        
        Args:
            audio_path: 참조 음성 파일 경로
            reference_text: 참조 음성의 대본 (옵션, 있으면 품질 향상)
            language: 참조 음성의 언어 코드
            
        Returns:
            성공 여부
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            logger.error(f"참조 음성 파일이 없습니다: {audio_path}")
            return False
        
        if language not in self.SUPPORTED_LANGUAGES:
            logger.error(f"지원하지 않는 언어: {language}")
            return False
        
        try:
            self._current_reference = {
                "path": str(audio_path),
                "text": reference_text,
                "language": language
            }
            
            # 실제 모델에 참조 음성 로드
            # if self._tts_engine:
            #     self._tts_engine.set_reference(
            #         audio_path=str(audio_path),
            #         text=reference_text,
            #         language=language
            #     )
            
            logger.info(f"참조 음성 로드 완료: {audio_path}")
            return True
            
        except Exception as e:
            logger.error(f"참조 음성 로드 실패: {e}")
            return False
    
    def synthesize(
        self,
        text: str,
        language: str = "ko",
        speed: float = 1.0,
        pitch_shift: float = 0.0,
        **kwargs
    ) -> Tuple[np.ndarray, int]:
        """
        텍스트를 음성으로 변환
        
        Args:
            text: 합성할 텍스트
            language: 타겟 언어 (기본: 한국어)
            speed: 재생 속도 (0.5 ~ 2.0)
            pitch_shift: 피치 시프트 (-12 ~ 12)
            **kwargs: 추가 옵션
            
        Returns:
            (audio_array, sample_rate) 튜플
        """
        if not self._is_initialized:
            self.initialize()
        
        if self._current_reference is None:
            raise ValueError("참조 음성이 로드되지 않았습니다. load_reference_audio()를 먼저 호출하세요.")
        
        # 텍스트 전처리
        text = self._preprocess_text(text, language)
        
        try:
            if self._tts_engine:
                # 실제 GPT-SoVITS 합성
                # audio = self._tts_engine.synthesize(
                #     text=text,
                #     language=language,
                #     speed=speed,
                #     **kwargs
                # )
                pass
            else:
                # 더미 출력 (테스트용)
                logger.warning("더미 모드: 무음 오디오를 반환합니다.")
                sample_rate = 44100
                duration = len(text) * 0.1  # 대략적인 길이 추정
                audio = np.zeros(int(sample_rate * duration), dtype=np.float32)
                return audio, sample_rate
            
        except Exception as e:
            logger.error(f"음성 합성 실패: {e}")
            raise
    
    def _preprocess_text(self, text: str, language: str) -> str:
        """
        텍스트 전처리
        
        Args:
            text: 입력 텍스트
            language: 언어 코드
            
        Returns:
            전처리된 텍스트
        """
        # 기본 정리
        text = text.strip()
        
        # 이모지 및 특수문자 제거
        import re
        text = re.sub(r'[📅📆🕐✅❌🔗💬📧🎤🔴🔊🔇•]', '', text)
        
        # 다중 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        # 언어별 추가 처리
        if language == "ko":
            # 한국어 G2P 처리는 별도 모듈에서
            pass
        elif language == "ja":
            # 일본어 처리
            pass
        
        return text
    
    def get_speaker_info(self) -> Optional[Dict[str, Any]]:
        """현재 참조 음성 정보 반환"""
        return self._current_reference
    
    @property
    def is_ready(self) -> bool:
        """음성 합성 준비 상태"""
        return self._is_initialized and self._current_reference is not None
    
    def unload(self):
        """모델 언로드 및 메모리 해제"""
        if self._tts_engine:
            # self._tts_engine.unload()
            pass
        
        self._gpt_model = None
        self._sovits_model = None
        self._is_initialized = False
        self._current_reference = None
        
        # GPU 메모리 해제
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        
        logger.info("모델 언로드 완료")


class G2PKConverter:
    """한국어 Grapheme-to-Phoneme 변환기"""
    
    def __init__(self):
        self._g2p = None
        self._initialize()
    
    def _initialize(self):
        """G2P 모듈 초기화"""
        try:
            from g2pk import G2p
            self._g2p = G2p()
        except ImportError:
            logger.warning("g2pk 라이브러리가 설치되지 않았습니다.")
    
    def convert(self, text: str) -> str:
        """
        한글 텍스트를 발음으로 변환
        
        Args:
            text: 한글 텍스트
            
        Returns:
            발음 변환된 텍스트
        """
        if self._g2p is None:
            return text
        
        return self._g2p(text)


class JapaneseConverter:
    """일본어 텍스트 처리"""
    
    def __init__(self):
        self._tokenizer = None
        self._initialize()
    
    def _initialize(self):
        """일본어 처리 모듈 초기화"""
        try:
            import fugashi
            self._tokenizer = fugashi.Tagger()
        except ImportError:
            logger.warning("fugashi 라이브러리가 설치되지 않았습니다.")
    
    def to_hiragana(self, text: str) -> str:
        """
        일본어를 히라가나로 변환
        
        Args:
            text: 일본어 텍스트
            
        Returns:
            히라가나 텍스트
        """
        try:
            import jaconv
            if self._tokenizer:
                words = self._tokenizer(text)
                result = ""
                for word in words:
                    if word.feature.kana:
                        result += jaconv.kata2hira(word.feature.kana)
                    else:
                        result += word.surface
                return result
        except Exception:
            pass
        
        return text

