"""
ASR Model Module
Whisper 모델 로드 및 추론
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class ASRModel:
    """Whisper ASR 모델 래퍼 클래스"""
    
    # 지원하는 모델 크기
    SUPPORTED_MODELS = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
    
    def __init__(
        self,
        model_name: str = "base",
        model_path: Optional[str] = None,
        device: str = "auto",
        language: str = "ko"
    ):
        """
        Args:
            model_name: Whisper 모델 크기 (tiny, base, small, medium, large)
            model_path: 모델 캐시 디렉토리
            device: 실행 디바이스 ("auto", "cpu", "cuda")
            language: 기본 언어
        """
        self.model_name = model_name
        self.model_path = model_path
        self.device = device
        self.language = language
        self.model = None
        self.is_loaded = False
    
    def load(self) -> bool:
        """모델 로드"""
        try:
            import whisper
            
            logger.info(f"Whisper 모델 로딩: {self.model_name}")
            
            # 디바이스 결정
            if self.device == "auto":
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                device = self.device
            
            logger.info(f"사용 디바이스: {device}")
            
            # 모델 로드
            if self.model_path:
                os.makedirs(self.model_path, exist_ok=True)
                self.model = whisper.load_model(
                    self.model_name,
                    device=device,
                    download_root=self.model_path
                )
            else:
                self.model = whisper.load_model(self.model_name, device=device)
            
            self.is_loaded = True
            logger.info("모델 로드 완료")
            return True
            
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            self.is_loaded = False
            return False
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> dict:
        """
        음성 파일을 텍스트로 변환
        
        Args:
            audio_path: 오디오 파일 경로
            language: 언어 코드 (None이면 자동 감지)
            task: "transcribe" 또는 "translate"
            
        Returns:
            {
                "text": 인식된 텍스트,
                "language": 감지된 언어,
                "duration": 오디오 길이 (초),
                "segments": 세그먼트 정보 리스트
            }
        """
        if not self.is_loaded:
            raise RuntimeError("모델이 로드되지 않았습니다. load()를 먼저 호출하세요.")
        
        # 언어 설정
        lang = language or self.language
        
        logger.info(f"음성 인식 시작: {audio_path}")
        
        # Whisper 추론
        result = self.model.transcribe(
            audio_path,
            language=lang if lang != "auto" else None,
            task=task,
            fp16=False,  # CPU 호환성
            verbose=False
        )
        
        # 오디오 길이 계산
        duration = 0.0
        if result.get("segments"):
            duration = result["segments"][-1].get("end", 0.0)
        
        logger.info(f"음성 인식 완료: {len(result['text'])} 자")
        
        return {
            "text": result["text"].strip(),
            "language": result.get("language", lang),
            "duration": duration,
            "segments": [
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"]
                }
                for seg in result.get("segments", [])
            ]
        }
    
    def unload(self):
        """모델 언로드 (메모리 해제)"""
        if self.model is not None:
            del self.model
            self.model = None
            self.is_loaded = False
            
            # GPU 메모리 해제
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
            
            logger.info("모델 언로드 완료")


class FasterWhisperModel(ASRModel):
    """
    Faster-Whisper 기반 ASR 모델 (최적화 버전)
    CTranslate2를 사용하여 더 빠른 추론 제공
    """
    
    def load(self) -> bool:
        """모델 로드"""
        try:
            from faster_whisper import WhisperModel
            
            logger.info(f"Faster-Whisper 모델 로딩: {self.model_name}")
            
            # 디바이스 및 컴퓨트 타입 결정
            if self.device == "auto":
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                    compute_type = "float16"
                else:
                    device = "cpu"
                    compute_type = "int8"
            else:
                device = self.device
                compute_type = "float16" if device == "cuda" else "int8"
            
            logger.info(f"사용 디바이스: {device}, 컴퓨트 타입: {compute_type}")
            
            self.model = WhisperModel(
                self.model_name,
                device=device,
                compute_type=compute_type,
                download_root=self.model_path
            )
            
            self.is_loaded = True
            logger.info("모델 로드 완료")
            return True
            
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            self.is_loaded = False
            return False
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> dict:
        """음성 파일을 텍스트로 변환"""
        if not self.is_loaded:
            raise RuntimeError("모델이 로드되지 않았습니다.")
        
        lang = language or self.language
        
        segments, info = self.model.transcribe(
            audio_path,
            language=lang if lang != "auto" else None,
            task=task,
            beam_size=5
        )
        
        # 결과 수집
        segment_list = list(segments)
        full_text = " ".join(seg.text for seg in segment_list)
        duration = segment_list[-1].end if segment_list else 0.0
        
        return {
            "text": full_text.strip(),
            "language": info.language,
            "duration": duration,
            "confidence": info.language_probability,
            "segments": [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text
                }
                for seg in segment_list
            ]
        }


