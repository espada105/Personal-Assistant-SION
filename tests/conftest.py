"""
Pytest Configuration and Fixtures
"""

import os
import sys
import pytest
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def project_root():
    """프로젝트 루트 디렉토리 반환"""
    return Path(__file__).parent.parent


@pytest.fixture
def sample_audio_path(tmp_path):
    """테스트용 샘플 오디오 파일 생성"""
    import numpy as np
    import wave
    
    # 1초 무음 WAV 파일 생성
    sample_rate = 16000
    duration = 1.0
    samples = int(sample_rate * duration)
    audio_data = np.zeros(samples, dtype=np.int16)
    
    audio_path = tmp_path / "test_audio.wav"
    
    with wave.open(str(audio_path), 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    return audio_path


@pytest.fixture
def mock_env_vars(monkeypatch):
    """테스트용 환경 변수 설정"""
    monkeypatch.setenv("API_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")


@pytest.fixture
def sample_nlu_texts():
    """NLU 테스트용 샘플 텍스트"""
    return [
        ("오늘 일정 알려줘", "schedule_check"),
        ("내일 오후 3시에 회의 잡아줘", "schedule_add"),
        ("새 이메일 있어?", "email_check"),
        ("파이썬이 뭐야?", "llm_chat"),
        ("날씨 어때?", "weather_check"),
    ]

