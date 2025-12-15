"""
Audio Utilities
오디오 처리 유틸리티 모듈
"""

import os
import numpy as np
import tempfile
from typing import Optional, Tuple, Union
from pathlib import Path

try:
    import librosa
    import soundfile as sf
    from scipy import signal
    AUDIO_LIBS_AVAILABLE = True
except ImportError:
    AUDIO_LIBS_AVAILABLE = False

try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class AudioProcessor:
    """오디오 처리 유틸리티 클래스"""
    
    def __init__(self, sample_rate: int = 44100):
        """
        Args:
            sample_rate: 기본 샘플링 레이트
        """
        self.sample_rate = sample_rate
        
        if not AUDIO_LIBS_AVAILABLE:
            raise ImportError("librosa, soundfile, scipy가 필요합니다.")
    
    def load_audio(
        self, 
        path: Union[str, Path], 
        target_sr: Optional[int] = None
    ) -> Tuple[np.ndarray, int]:
        """
        오디오 파일 로드
        
        Args:
            path: 오디오 파일 경로
            target_sr: 목표 샘플링 레이트 (None이면 원본 유지)
            
        Returns:
            (audio_data, sample_rate) 튜플
        """
        audio, sr = librosa.load(str(path), sr=target_sr)
        return audio, sr
    
    def save_audio(
        self, 
        audio: np.ndarray, 
        path: Union[str, Path],
        sample_rate: Optional[int] = None
    ):
        """
        오디오를 파일로 저장
        
        Args:
            audio: 오디오 데이터
            path: 저장 경로
            sample_rate: 샘플링 레이트
        """
        sr = sample_rate or self.sample_rate
        sf.write(str(path), audio, sr)
    
    def normalize_audio(
        self, 
        audio: np.ndarray, 
        target_db: float = -20.0
    ) -> np.ndarray:
        """
        오디오 정규화 (볼륨 조정)
        
        Args:
            audio: 입력 오디오
            target_db: 목표 dB 레벨
            
        Returns:
            정규화된 오디오
        """
        rms = np.sqrt(np.mean(audio ** 2))
        if rms > 0:
            target_rms = 10 ** (target_db / 20)
            audio = audio * (target_rms / rms)
        return np.clip(audio, -1.0, 1.0)
    
    def remove_silence(
        self, 
        audio: np.ndarray,
        sample_rate: int,
        top_db: float = 30
    ) -> np.ndarray:
        """
        무음 구간 제거
        
        Args:
            audio: 입력 오디오
            sample_rate: 샘플링 레이트
            top_db: 무음 판단 기준 (dB)
            
        Returns:
            무음이 제거된 오디오
        """
        intervals = librosa.effects.split(audio, top_db=top_db)
        if len(intervals) == 0:
            return audio
        
        non_silent = []
        for start, end in intervals:
            non_silent.append(audio[start:end])
        
        return np.concatenate(non_silent)
    
    def resample(
        self, 
        audio: np.ndarray, 
        orig_sr: int, 
        target_sr: int
    ) -> np.ndarray:
        """
        오디오 리샘플링
        
        Args:
            audio: 입력 오디오
            orig_sr: 원본 샘플링 레이트
            target_sr: 목표 샘플링 레이트
            
        Returns:
            리샘플링된 오디오
        """
        if orig_sr == target_sr:
            return audio
        return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
    
    def add_fade(
        self, 
        audio: np.ndarray,
        sample_rate: int,
        fade_in_ms: float = 10,
        fade_out_ms: float = 10
    ) -> np.ndarray:
        """
        페이드 인/아웃 효과 추가
        
        Args:
            audio: 입력 오디오
            sample_rate: 샘플링 레이트
            fade_in_ms: 페이드 인 시간 (ms)
            fade_out_ms: 페이드 아웃 시간 (ms)
            
        Returns:
            페이드가 적용된 오디오
        """
        audio = audio.copy()
        
        # 페이드 인
        fade_in_samples = int(sample_rate * fade_in_ms / 1000)
        if fade_in_samples > 0 and fade_in_samples < len(audio):
            fade_in = np.linspace(0, 1, fade_in_samples)
            audio[:fade_in_samples] *= fade_in
        
        # 페이드 아웃
        fade_out_samples = int(sample_rate * fade_out_ms / 1000)
        if fade_out_samples > 0 and fade_out_samples < len(audio):
            fade_out = np.linspace(1, 0, fade_out_samples)
            audio[-fade_out_samples:] *= fade_out
        
        return audio
    
    def pitch_shift(
        self, 
        audio: np.ndarray,
        sample_rate: int,
        semitones: float
    ) -> np.ndarray:
        """
        피치 시프트
        
        Args:
            audio: 입력 오디오
            sample_rate: 샘플링 레이트
            semitones: 반음 단위 시프트 (-12 ~ 12)
            
        Returns:
            피치 시프트된 오디오
        """
        if semitones == 0:
            return audio
        return librosa.effects.pitch_shift(
            audio, sr=sample_rate, n_steps=semitones
        )
    
    def change_speed(
        self, 
        audio: np.ndarray,
        speed_factor: float
    ) -> np.ndarray:
        """
        재생 속도 변경
        
        Args:
            audio: 입력 오디오
            speed_factor: 속도 배율 (0.5 ~ 2.0)
            
        Returns:
            속도 조정된 오디오
        """
        if speed_factor == 1.0:
            return audio
        return librosa.effects.time_stretch(audio, rate=speed_factor)
    
    def get_duration(
        self, 
        audio: np.ndarray,
        sample_rate: int
    ) -> float:
        """
        오디오 길이 반환 (초)
        """
        return len(audio) / sample_rate
    
    def to_mono(self, audio: np.ndarray) -> np.ndarray:
        """
        스테레오를 모노로 변환
        """
        if len(audio.shape) > 1:
            return np.mean(audio, axis=1)
        return audio


class AudioPlayer:
    """오디오 재생 클래스"""
    
    def __init__(self):
        if not PYGAME_AVAILABLE:
            raise ImportError("pygame이 필요합니다.")
        
        self._is_playing = False
    
    def play(
        self, 
        audio: np.ndarray, 
        sample_rate: int = 44100,
        block: bool = True
    ):
        """
        오디오 재생
        
        Args:
            audio: 오디오 데이터 (numpy array)
            sample_rate: 샘플링 레이트
            block: True면 재생 완료까지 대기
        """
        # 임시 파일에 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp_path = tmp.name
            sf.write(tmp_path, audio, sample_rate)
        
        try:
            self._is_playing = True
            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()
            
            if block:
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)
        finally:
            self._is_playing = False
            try:
                os.remove(tmp_path)
            except:
                pass
    
    def play_file(self, path: Union[str, Path], block: bool = True):
        """
        파일 재생
        
        Args:
            path: 오디오 파일 경로
            block: True면 재생 완료까지 대기
        """
        self._is_playing = True
        pygame.mixer.music.load(str(path))
        pygame.mixer.music.play()
        
        if block:
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
        
        self._is_playing = False
    
    def stop(self):
        """재생 중지"""
        pygame.mixer.music.stop()
        self._is_playing = False
    
    def pause(self):
        """재생 일시정지"""
        pygame.mixer.music.pause()
    
    def resume(self):
        """재생 재개"""
        pygame.mixer.music.unpause()
    
    def set_volume(self, volume: float):
        """
        볼륨 설정
        
        Args:
            volume: 0.0 ~ 1.0
        """
        pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
    
    @property
    def is_playing(self) -> bool:
        """재생 중 여부"""
        return self._is_playing and pygame.mixer.music.get_busy()

