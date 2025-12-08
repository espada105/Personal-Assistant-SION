"""
Configuration Module
클라이언트 설정 관리
"""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # API 설정
    API_BASE_URL: str = Field(
        default="http://localhost:8000",
        description="백엔드 API 서버 URL"
    )
    API_KEY: Optional[str] = Field(
        default=None,
        description="API 인증 키"
    )
    
    # AWS 설정
    AWS_REGION: str = Field(
        default="ap-northeast-2",
        description="AWS 리전"
    )
    AWS_ACCESS_KEY_ID: Optional[str] = Field(
        default=None,
        description="AWS Access Key ID"
    )
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(
        default=None,
        description="AWS Secret Access Key"
    )
    
    # 오디오 설정
    AUDIO_SAMPLE_RATE: int = Field(
        default=16000,
        description="오디오 샘플링 레이트"
    )
    AUDIO_CHANNELS: int = Field(
        default=1,
        description="오디오 채널 수"
    )
    AUDIO_MAX_DURATION: float = Field(
        default=10.0,
        description="최대 녹음 시간 (초)"
    )
    
    # 로깅 설정
    LOG_LEVEL: str = Field(
        default="INFO",
        description="로그 레벨"
    )
    LOG_FILE: Optional[str] = Field(
        default=None,
        description="로그 파일 경로"
    )
    
    # 핫키 설정
    HOTKEY_ACTIVATE: str = Field(
        default="ctrl+shift+s",
        description="비서 활성화 핫키"
    )
    HOTKEY_CANCEL: str = Field(
        default="escape",
        description="취소 핫키"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 설정 싱글톤
settings = Settings()


def get_project_root() -> Path:
    """프로젝트 루트 디렉토리 반환"""
    return Path(__file__).parent.parent.parent


def get_config_dir() -> Path:
    """설정 디렉토리 반환"""
    return get_project_root() / "configs"


def load_env_file(env_path: Optional[str] = None):
    """환경 변수 파일 로드"""
    from dotenv import load_dotenv
    
    if env_path:
        load_dotenv(env_path)
    else:
        # 기본 경로에서 .env 파일 찾기
        default_paths = [
            get_config_dir() / ".env",
            get_project_root() / ".env",
            Path.cwd() / ".env"
        ]
        
        for path in default_paths:
            if path.exists():
                load_dotenv(path)
                break

