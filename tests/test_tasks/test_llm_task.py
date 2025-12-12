"""
LLM Task Tests
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock


class TestLLMTask:
    """LLM 태스크 테스트"""
    
    @pytest.fixture
    def llm_task(self):
        """LLM 태스크 인스턴스 (API 키 없이)"""
        from backend.task_executor.app.tasks.llm_task import LLMTask
        
        return LLMTask(api_key=None)
    
    def test_initialization(self, llm_task):
        """초기화 테스트"""
        assert llm_task.model == "gpt-3.5-turbo"
        assert llm_task.client is None  # API 키 없으면 클라이언트 없음
    
    @pytest.mark.asyncio
    async def test_chat_without_api(self, llm_task):
        """API 없이 대화 테스트 (더미 응답)"""
        result = await llm_task.execute("chat", {
            "message": "안녕하세요"
        })
        
        assert "response" in result
        assert "conversation_id" in result
        # API 없으면 더미 응답
        assert "데모 모드" in result["response"] or "설정되지 않았습니다" in result["response"]
    
    @pytest.mark.asyncio
    async def test_conversation_id_generation(self, llm_task):
        """대화 ID 생성 테스트"""
        result = await llm_task.execute("chat", {
            "message": "테스트"
        })
        
        assert result["conversation_id"] is not None
    
    @pytest.mark.asyncio
    @patch('backend.task_executor.app.tasks.llm_task.OpenAI')
    async def test_chat_with_mock_api(self, mock_openai):
        """Mock API로 대화 테스트"""
        from backend.task_executor.app.tasks.llm_task import LLMTask
        
        # Mock 설정
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "안녕하세요! 무엇을 도와드릴까요?"
        mock_response.usage.total_tokens = 50
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        llm_task = LLMTask(api_key="test-key")
        llm_task.client = mock_client
        
        result = await llm_task.execute("chat", {
            "message": "안녕하세요"
        })
        
        assert "response" in result
        assert result["tokens_used"] == 50
    
    def test_clear_conversation(self, llm_task):
        """대화 히스토리 삭제 테스트"""
        # 더미 히스토리 추가
        llm_task.conversations["test_conv"] = [
            {"role": "user", "content": "테스트"}
        ]
        
        llm_task.clear_conversation("test_conv")
        
        assert "test_conv" not in llm_task.conversations


class TestCalendarTask:
    """캘린더 태스크 테스트"""
    
    @pytest.fixture
    def calendar_task(self):
        """캘린더 태스크 인스턴스"""
        from backend.task_executor.app.tasks.calendar_task import CalendarTask
        
        return CalendarTask(credentials_path=None)
    
    def test_parse_date_entity(self, calendar_task):
        """날짜 파싱 테스트"""
        from datetime import datetime, timedelta
        
        today = datetime.now().date()
        
        # 오늘
        result = calendar_task._parse_date_entity("오늘")
        assert result.date() == today
        
        # 내일
        result = calendar_task._parse_date_entity("내일")
        assert result.date() == today + timedelta(days=1)
    
    def test_parse_time_entity(self, calendar_task):
        """시간 파싱 테스트"""
        # 오후 3시
        hour, minute = calendar_task._parse_time_entity("오후 3시")
        assert hour == 15
        assert minute == 0
        
        # 오전 9시 30분
        hour, minute = calendar_task._parse_time_entity("오전 9시 30분")
        assert hour == 9
        assert minute == 30
    
    @pytest.mark.asyncio
    async def test_check_events_demo_mode(self, calendar_task):
        """데모 모드 일정 확인 테스트"""
        result = await calendar_task.execute("check", {"date": "오늘"})
        
        assert "events" in result
        assert "데모 모드" in result["message"]


class TestTaskExecutorAPI:
    """Task Executor API 테스트"""
    
    @pytest.fixture
    def client(self):
        """FastAPI 테스트 클라이언트"""
        from fastapi.testclient import TestClient
        from backend.task_executor.app.main import app
        
        return TestClient(app)
    
    def test_health_check(self, client):
        """헬스체크 엔드포인트 테스트"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "task_executor"
    
    def test_list_tasks(self, client):
        """작업 목록 엔드포인트 테스트"""
        response = client.get("/tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "handlers" in data


