"""
ASR Model Tests
"""

import pytest
from unittest.mock import Mock, patch


class TestASRModel:
    """ASR 모델 테스트"""
    
    def test_model_initialization(self):
        """모델 초기화 테스트"""
        # 실제 모델 로드 없이 테스트
        from backend.asr.app.model import ASRModel
        
        model = ASRModel(model_name="base", device="cpu")
        
        assert model.model_name == "base"
        assert model.device == "cpu"
        assert model.is_loaded is False
    
    def test_supported_models(self):
        """지원 모델 목록 테스트"""
        from backend.asr.app.model import ASRModel
        
        assert "tiny" in ASRModel.SUPPORTED_MODELS
        assert "base" in ASRModel.SUPPORTED_MODELS
        assert "large" in ASRModel.SUPPORTED_MODELS
    
    @pytest.mark.skipif(
        True,  # CI 환경에서는 실제 모델 로드 스킵
        reason="Requires actual Whisper model"
    )
    def test_model_load(self):
        """모델 로드 테스트 (실제 모델 필요)"""
        from backend.asr.app.model import ASRModel
        
        model = ASRModel(model_name="tiny", device="cpu")
        result = model.load()
        
        assert result is True
        assert model.is_loaded is True
    
    @patch('backend.asr.app.model.whisper')
    def test_transcribe_mock(self, mock_whisper, sample_audio_path):
        """음성 인식 테스트 (Mock)"""
        from backend.asr.app.model import ASRModel
        
        # Mock 설정
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "text": "테스트 텍스트입니다.",
            "language": "ko",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "테스트 텍스트입니다."}
            ]
        }
        mock_whisper.load_model.return_value = mock_model
        
        model = ASRModel(model_name="base", device="cpu")
        model.load()
        
        result = model.transcribe(str(sample_audio_path))
        
        assert "text" in result
        assert result["language"] == "ko"


class TestASRAPI:
    """ASR API 테스트"""
    
    @pytest.fixture
    def client(self):
        """FastAPI 테스트 클라이언트"""
        from fastapi.testclient import TestClient
        from backend.asr.app.main import app
        
        return TestClient(app)
    
    def test_health_check(self, client):
        """헬스체크 엔드포인트 테스트"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "asr"

