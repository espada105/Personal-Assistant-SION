"""
Intent Classifier Module
의도 분류 및 엔티티 추출 모델
"""

import logging
import os
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class IntentClassifier:
    """의도 분류 클래스"""
    
    # 지원하는 의도 목록
    SUPPORTED_INTENTS = {
        "schedule_check": "일정 확인",
        "schedule_add": "일정 추가",
        "schedule_delete": "일정 삭제",
        "email_check": "이메일 확인",
        "email_send": "이메일 전송",
        "file_search": "파일 검색",
        "file_open": "파일 열기",
        "app_open": "앱 실행",
        "web_search": "웹 검색",
        "weather_check": "날씨 확인",
        "timer_set": "타이머 설정",
        "reminder_set": "리마인더 설정",
        "llm_chat": "일반 대화/질문",
        "system_control": "시스템 제어",
        "unknown": "알 수 없음"
    }
    
    # 의도별 키워드 패턴 (규칙 기반 폴백)
    INTENT_PATTERNS = {
        "schedule_check": [r"일정", r"스케줄", r"약속", r"오늘\s*뭐", r"언제"],
        "schedule_add": [r"일정\s*(추가|등록|잡아)", r"약속\s*(잡아|만들어)"],
        "schedule_delete": [r"일정\s*(삭제|취소)", r"약속\s*(취소|삭제)"],
        "email_check": [r"이메일\s*(확인|읽어)", r"메일\s*(확인|읽어)", r"새\s*메일"],
        "email_send": [r"이메일\s*(보내|전송)", r"메일\s*(보내|전송)"],
        "file_search": [r"파일\s*(찾아|검색)", r"어디.*있", r"폴더"],
        "file_open": [r"파일\s*(열어|실행)", r"문서\s*열어"],
        "app_open": [r"(실행|열어|켜).*(앱|프로그램|어플)", r"(크롬|브라우저|메모장|계산기)"],
        "web_search": [r"검색", r"찾아.*줘", r"알려.*줘"],
        "weather_check": [r"날씨", r"기온", r"비\s*올까"],
        "timer_set": [r"타이머", r"알람", r"분\s*후"],
        "reminder_set": [r"리마인더", r"알림", r"까먹지"],
        "system_control": [r"볼륨", r"음량", r"밝기", r"종료", r"재부팅"],
    }
    
    # 엔티티 추출 패턴
    ENTITY_PATTERNS = {
        "time": r"(\d{1,2}시\s*\d{0,2}분?|\d{1,2}:\d{2}|오전\s*\d{1,2}시|오후\s*\d{1,2}시)",
        "date": r"(오늘|내일|모레|\d{1,2}월\s*\d{1,2}일|다음\s*주|이번\s*주)",
        "duration": r"(\d+\s*(분|시간|초))",
        "person": r"([가-힣]{2,4}(?:씨|님|에게))",
        "app_name": r"(크롬|브라우저|메모장|계산기|엑셀|워드|파워포인트|비주얼\s*스튜디오)",
        "file_name": r"([가-힣a-zA-Z0-9_]+\.(txt|pdf|doc|docx|xlsx|pptx|py|js))",
    }
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Args:
            model_path: 학습된 모델 경로 (None이면 규칙 기반)
        """
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.use_ml_model = False
    
    def load(self) -> bool:
        """모델 로드"""
        try:
            # ML 모델 로드 시도
            if self.model_path and os.path.exists(os.path.join(self.model_path, "intent_model")):
                self._load_ml_model()
            else:
                # 규칙 기반 모드
                logger.info("규칙 기반 의도 분류기 초기화")
                self.use_ml_model = False
            
            self.is_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            # 폴백: 규칙 기반
            self.use_ml_model = False
            self.is_loaded = True
            return True
    
    def _load_ml_model(self):
        """Transformers 기반 ML 모델 로드"""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            
            model_dir = os.path.join(self.model_path, "intent_model")
            
            logger.info(f"ML 모델 로딩: {model_dir}")
            self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
            self.use_ml_model = True
            logger.info("ML 모델 로드 완료")
            
        except Exception as e:
            logger.warning(f"ML 모델 로드 실패, 규칙 기반 사용: {e}")
            self.use_ml_model = False
    
    def analyze(self, text: str) -> Dict:
        """
        텍스트 분석 (의도 분류 + 엔티티 추출)
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            {
                "intent": 의도 이름,
                "intent_confidence": 신뢰도,
                "entities": 추출된 엔티티 리스트
            }
        """
        # 의도 분류
        intent, confidence = self.classify_intent(text)
        
        # 엔티티 추출
        entities = self.extract_entities(text)
        
        return {
            "intent": intent,
            "intent_confidence": confidence,
            "entities": entities
        }
    
    def classify_intent(self, text: str) -> Tuple[str, float]:
        """
        의도 분류
        
        Args:
            text: 분류할 텍스트
            
        Returns:
            (의도 이름, 신뢰도)
        """
        if self.use_ml_model and self.model is not None:
            return self._classify_with_ml(text)
        else:
            return self._classify_with_rules(text)
    
    def _classify_with_ml(self, text: str) -> Tuple[str, float]:
        """ML 모델을 사용한 의도 분류"""
        import torch
        
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=128,
            padding=True
        )
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)
            pred_idx = torch.argmax(probs, dim=-1).item()
            confidence = probs[0][pred_idx].item()
        
        intents = list(self.SUPPORTED_INTENTS.keys())
        intent = intents[pred_idx] if pred_idx < len(intents) else "unknown"
        
        return intent, confidence
    
    def _classify_with_rules(self, text: str) -> Tuple[str, float]:
        """규칙 기반 의도 분류"""
        text_lower = text.lower()
        
        best_intent = "unknown"
        best_score = 0.0
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    score += 1
            
            # 정규화된 점수 계산
            if score > 0:
                normalized_score = min(score / len(patterns), 1.0)
                if normalized_score > best_score:
                    best_score = normalized_score
                    best_intent = intent
        
        # 매칭되는 패턴이 없으면 LLM 대화로 분류
        if best_intent == "unknown" and len(text) > 5:
            best_intent = "llm_chat"
            best_score = 0.5
        
        # 신뢰도 보정
        confidence = 0.3 + (best_score * 0.6)  # 0.3 ~ 0.9 범위
        
        return best_intent, confidence
    
    def extract_entities(self, text: str) -> List[Dict]:
        """
        엔티티 추출
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            추출된 엔티티 리스트
        """
        entities = []
        
        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                entities.append({
                    "type": entity_type,
                    "value": match.group(0),
                    "start": match.start(),
                    "end": match.end()
                })
        
        return entities
    
    def get_supported_intents(self) -> Dict[str, str]:
        """지원하는 의도 목록 반환"""
        return self.SUPPORTED_INTENTS.copy()


class TransformerIntentClassifier(IntentClassifier):
    """
    Transformer 기반 의도 분류기
    사전 학습된 한국어 모델 사용
    """
    
    def __init__(
        self,
        model_name: str = "klue/bert-base",
        model_path: Optional[str] = None
    ):
        super().__init__(model_path)
        self.model_name = model_name
    
    def load(self) -> bool:
        """모델 로드"""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            
            logger.info(f"Transformer 모델 로딩: {self.model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Fine-tuned 모델이 있으면 로드, 없으면 base 모델
            if self.model_path and os.path.exists(self.model_path):
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_path,
                    num_labels=len(self.SUPPORTED_INTENTS)
                )
            else:
                # Base 모델 로드 (fine-tuning 필요)
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    self.model_name,
                    num_labels=len(self.SUPPORTED_INTENTS)
                )
            
            self.use_ml_model = True
            self.is_loaded = True
            logger.info("모델 로드 완료")
            return True
            
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            return super().load()  # 규칙 기반으로 폴백


