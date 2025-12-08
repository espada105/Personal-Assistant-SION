"""
Intent Classifier Tests
"""

import pytest


class TestIntentClassifier:
    """의도 분류기 테스트"""
    
    @pytest.fixture
    def classifier(self):
        """분류기 인스턴스"""
        from backend.nlu.app.intent_classifier import IntentClassifier
        
        clf = IntentClassifier()
        clf.load()
        return clf
    
    def test_classifier_initialization(self, classifier):
        """분류기 초기화 테스트"""
        assert classifier.is_loaded is True
    
    def test_supported_intents(self, classifier):
        """지원 의도 목록 테스트"""
        intents = classifier.get_supported_intents()
        
        assert "schedule_check" in intents
        assert "email_check" in intents
        assert "llm_chat" in intents
    
    @pytest.mark.parametrize("text,expected_intent", [
        ("오늘 일정 알려줘", "schedule_check"),
        ("내일 오후 3시에 회의 잡아줘", "schedule_add"),
        ("새 이메일 확인해줘", "email_check"),
    ])
    def test_rule_based_classification(self, classifier, text, expected_intent):
        """규칙 기반 의도 분류 테스트"""
        intent, confidence = classifier.classify_intent(text)
        
        assert intent == expected_intent
        assert 0.0 <= confidence <= 1.0
    
    def test_entity_extraction(self, classifier):
        """엔티티 추출 테스트"""
        text = "내일 오후 3시에 회의"
        
        entities = classifier.extract_entities(text)
        
        # 날짜 엔티티 확인
        date_entities = [e for e in entities if e["type"] == "date"]
        assert len(date_entities) >= 1
        
        # 시간 엔티티 확인
        time_entities = [e for e in entities if e["type"] == "time"]
        assert len(time_entities) >= 1
    
    def test_analyze_full(self, classifier):
        """전체 분석 (의도 + 엔티티) 테스트"""
        text = "내일 오후 3시에 김철수씨와 회의 일정 잡아줘"
        
        result = classifier.analyze(text)
        
        assert "intent" in result
        assert "intent_confidence" in result
        assert "entities" in result
        assert result["intent"] == "schedule_add"
    
    def test_unknown_intent_fallback(self, classifier):
        """알 수 없는 의도 폴백 테스트"""
        text = "이건 정말 이상한 문장이네"
        
        intent, confidence = classifier.classify_intent(text)
        
        # 긴 텍스트는 llm_chat으로 폴백
        assert intent in ["unknown", "llm_chat"]


class TestNLUAPI:
    """NLU API 테스트"""
    
    @pytest.fixture
    def client(self):
        """FastAPI 테스트 클라이언트"""
        from fastapi.testclient import TestClient
        from backend.nlu.app.main import app
        
        return TestClient(app)
    
    def test_health_check(self, client):
        """헬스체크 엔드포인트 테스트"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "nlu"
    
    def test_analyze_endpoint(self, client):
        """분석 엔드포인트 테스트"""
        response = client.post(
            "/analyze",
            json={"text": "오늘 일정 알려줘"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "intent" in data
        assert "entities" in data
    
    def test_intents_endpoint(self, client):
        """의도 목록 엔드포인트 테스트"""
        response = client.get("/intents")
        
        assert response.status_code == 200
        data = response.json()
        assert "intents" in data

