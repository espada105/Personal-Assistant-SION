"""
LLM-based Agent
GPT가 직접 의도를 파악하고 함수를 호출하는 에이전트
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Google Services
try:
    from google_services import get_calendar_service, get_gmail_service
    GOOGLE_AVAILABLE = True
except ImportError:
    try:
        from .google_services import get_calendar_service, get_gmail_service
        GOOGLE_AVAILABLE = True
    except ImportError:
        GOOGLE_AVAILABLE = False


# 사용 가능한 함수(도구) 정의
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_calendar",
            "description": "오늘 또는 특정 날짜의 일정을 확인합니다. 예: '오늘 일정', '내일 뭐 있어?', '이번 주 일정'",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "확인할 날짜. 'today', 'tomorrow', 또는 'YYYY-MM-DD' 형식",
                        "default": "today"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_calendar_event",
            "description": "새로운 일정을 추가합니다. 예: '내일 3시에 회의', '금요일 오후 2시 미팅 잡아줘'",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "일정 제목"
                    },
                    "date": {
                        "type": "string",
                        "description": "날짜. 'today', 'tomorrow', 또는 'YYYY-MM-DD' 형식"
                    },
                    "time": {
                        "type": "string",
                        "description": "시간. 'HH:MM' 24시간 형식 (예: '15:00')"
                    },
                    "duration": {
                        "type": "integer",
                        "description": "일정 길이 (분 단위). 기본값 60",
                        "default": 60
                    }
                },
                "required": ["title", "date", "time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_calendar_event",
            "description": "기존 일정을 수정합니다. 예: '3시 회의를 4시로 변경해줘', '미팅 제목을 바꿔줘'",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_query": {
                        "type": "string",
                        "description": "수정할 일정을 찾기 위한 검색어 (일정 제목)"
                    },
                    "new_title": {
                        "type": "string",
                        "description": "새로운 일정 제목 (변경할 경우)"
                    },
                    "new_date": {
                        "type": "string",
                        "description": "새로운 날짜. 'today', 'tomorrow', 또는 'YYYY-MM-DD' 형식"
                    },
                    "new_time": {
                        "type": "string",
                        "description": "새로운 시간. 'HH:MM' 24시간 형식 (예: '16:00')"
                    }
                },
                "required": ["search_query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_calendar_event",
            "description": "일정을 삭제/취소합니다. 예: '내일 미팅 취소해줘', '회의 일정 삭제해줘'",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_query": {
                        "type": "string",
                        "description": "삭제할 일정을 찾기 위한 검색어 (일정 제목)"
                    }
                },
                "required": ["search_query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_email",
            "description": "읽지 않은 이메일을 확인합니다. 예: '새 메일 있어?', '이메일 확인해줘', '오늘 온 메일'",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_count": {
                        "type": "integer",
                        "description": "확인할 최대 이메일 수",
                        "default": 5
                    }
                },
                "required": []
            }
        }
    }
]

# 시스템 프롬프트
SYSTEM_PROMPT = """당신은 SION이라는 친절한 개인 비서 AI입니다.

사용자의 요청을 이해하고 적절한 도구(함수)를 사용하여 도움을 드립니다.

사용 가능한 기능:
1. 일정 확인 - 오늘/내일/특정 날짜의 캘린더 일정 확인
2. 일정 추가 - 새로운 일정을 캘린더에 추가
3. 일정 수정 - 기존 일정의 시간이나 제목 변경
4. 일정 삭제 - 일정 취소/삭제
5. 이메일 확인 - 읽지 않은 이메일 확인

일정이나 이메일 관련 요청이면 반드시 해당 함수를 호출하세요.
그 외의 일반적인 질문에는 직접 답변해주세요.

항상 한국어로 친절하게 응답하세요."""


class LLMAgent:
    """LLM 기반 에이전트"""
    
    def __init__(self):
        self.client = None
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
        self._init_client()
    
    def _init_client(self):
        """OpenAI 클라이언트 초기화"""
        if not OPENAI_AVAILABLE:
            return
        
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "여기에-API-키-입력":
            self.client = OpenAI(api_key=api_key)
    
    def process(self, user_message: str) -> str:
        """사용자 메시지 처리"""
        if not self.client:
            return "❌ OpenAI API 키가 설정되지 않았습니다.\n\nconfigs/.env 파일을 확인해주세요."
        
        try:
            # GPT에게 메시지 전송 (함수 호출 가능)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=1000
            )
            
            message = response.choices[0].message
            
            # 함수 호출이 필요한 경우
            if message.tool_calls:
                return self._handle_tool_calls(message.tool_calls, user_message)
            
            # 일반 텍스트 응답
            return f"💬 {message.content}"
            
        except Exception as e:
            return f"❌ 오류 발생: {str(e)}"
    
    def _handle_tool_calls(self, tool_calls, original_message: str) -> str:
        """함수 호출 처리"""
        results = []
        
        for tool_call in tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            
            print(f"[Agent] 함수 호출: {func_name}({func_args})")
            
            if func_name == "check_calendar":
                result = self._check_calendar(func_args)
            elif func_name == "add_calendar_event":
                result = self._add_calendar_event(func_args)
            elif func_name == "update_calendar_event":
                result = self._update_calendar_event(func_args)
            elif func_name == "delete_calendar_event":
                result = self._delete_calendar_event(func_args)
            elif func_name == "check_email":
                result = self._check_email(func_args)
            else:
                result = f"알 수 없는 함수: {func_name}"
            
            results.append(result)
        
        return "\n\n".join(results)
    
    def _check_calendar(self, args: Dict[str, Any]) -> str:
        """일정 확인"""
        if not GOOGLE_AVAILABLE:
            return "📅 Google 캘린더가 연결되지 않았습니다.\n\n'Google 로그인' 버튼을 클릭해주세요."
        
        try:
            calendar = get_calendar_service()
            date_str = args.get("date", "today")
            
            if date_str == "today":
                events = calendar.get_today_events()
                date_label = "오늘"
            elif date_str == "tomorrow":
                events = calendar.get_tomorrow_events()
                date_label = "내일"
            else:
                # 특정 날짜 처리 (추후 구현)
                events = calendar.get_today_events()
                date_label = date_str
            
            if not events:
                return f"📅 {date_label} 일정이 없습니다."
            
            response = f"📅 {date_label} 일정 ({len(events)}개):\n\n"
            for event in events:
                time_str = event['start']
                if 'T' in time_str:
                    time_str = time_str.split('T')[1][:5]
                response += f"• {time_str} - {event['title']}\n"
            
            return response
            
        except Exception as e:
            return f"📅 일정 확인 오류: {str(e)}"
    
    def _add_calendar_event(self, args: Dict[str, Any]) -> str:
        """일정 추가"""
        if not GOOGLE_AVAILABLE:
            return "📅 Google 캘린더가 연결되지 않았습니다."
        
        try:
            calendar = get_calendar_service()
            
            title = args.get("title", "새 일정")
            date_str = args.get("date", "today")
            time_str = args.get("time", "09:00")
            duration = args.get("duration", 60)
            
            # 날짜 파싱
            if date_str == "today":
                event_date = datetime.now()
            elif date_str == "tomorrow":
                event_date = datetime.now() + timedelta(days=1)
            else:
                try:
                    event_date = datetime.strptime(date_str, "%Y-%m-%d")
                except:
                    event_date = datetime.now()
            
            # 시간 파싱
            try:
                hour, minute = map(int, time_str.split(":"))
            except:
                hour, minute = 9, 0
            
            start_time = event_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            result = calendar.create_event(title, start_time, duration)
            
            if result:
                return f"✅ 일정이 추가되었습니다!\n\n📅 {title}\n🕐 {start_time.strftime('%Y-%m-%d %H:%M')}"
            else:
                return "❌ 일정 추가에 실패했습니다."
            
        except Exception as e:
            return f"📅 일정 추가 오류: {str(e)}"
    
    def _update_calendar_event(self, args: Dict[str, Any]) -> str:
        """일정 수정"""
        if not GOOGLE_AVAILABLE:
            return "📅 Google 캘린더가 연결되지 않았습니다."
        
        try:
            calendar = get_calendar_service()
            search_query = args.get("search_query", "")
            
            # 일정 검색
            events = calendar.search_events(search_query, max_results=1)
            
            if not events:
                return f"📅 '{search_query}' 일정을 찾을 수 없습니다."
            
            event = events[0]
            event_id = event['id']
            
            # 새로운 시간 파싱
            new_time = None
            new_date = args.get("new_date")
            new_time_str = args.get("new_time")
            
            if new_date or new_time_str:
                # 날짜 파싱
                if new_date == "today":
                    event_date = datetime.now()
                elif new_date == "tomorrow":
                    event_date = datetime.now() + timedelta(days=1)
                elif new_date:
                    try:
                        event_date = datetime.strptime(new_date, "%Y-%m-%d")
                    except:
                        event_date = datetime.now()
                else:
                    # 기존 날짜 유지
                    from dateutil import parser
                    event_date = parser.parse(event['start'])
                
                # 시간 파싱
                if new_time_str:
                    try:
                        hour, minute = map(int, new_time_str.split(":"))
                    except:
                        hour, minute = 9, 0
                else:
                    hour, minute = event_date.hour, event_date.minute
                
                new_time = event_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # 수정 실행
            new_title = args.get("new_title")
            result = calendar.update_event(event_id, title=new_title, start_time=new_time)
            
            if result:
                changes = []
                if new_title:
                    changes.append(f"제목: {new_title}")
                if new_time:
                    changes.append(f"시간: {new_time.strftime('%Y-%m-%d %H:%M')}")
                
                return f"✅ 일정이 수정되었습니다!\n\n📅 {event['title']}\n변경사항: {', '.join(changes)}"
            else:
                return "❌ 일정 수정에 실패했습니다."
            
        except Exception as e:
            return f"📅 일정 수정 오류: {str(e)}"
    
    def _delete_calendar_event(self, args: Dict[str, Any]) -> str:
        """일정 삭제"""
        if not GOOGLE_AVAILABLE:
            return "📅 Google 캘린더가 연결되지 않았습니다."
        
        try:
            calendar = get_calendar_service()
            search_query = args.get("search_query", "")
            
            # 일정 검색
            events = calendar.search_events(search_query, max_results=1)
            
            if not events:
                return f"📅 '{search_query}' 일정을 찾을 수 없습니다."
            
            event = events[0]
            event_id = event['id']
            event_title = event['title']
            event_start = event['start']
            
            # 삭제 실행
            if calendar.delete_event(event_id):
                return f"✅ 일정이 삭제되었습니다!\n\n🗑️ {event_title}\n📆 {event_start}"
            else:
                return "❌ 일정 삭제에 실패했습니다."
            
        except Exception as e:
            return f"📅 일정 삭제 오류: {str(e)}"
    
    def _check_email(self, args: Dict[str, Any]) -> str:
        """이메일 확인"""
        if not GOOGLE_AVAILABLE:
            return "📧 Gmail이 연결되지 않았습니다.\n\n'Google 로그인' 버튼을 클릭해주세요."
        
        try:
            gmail = get_gmail_service()
            max_count = args.get("max_count", 5)
            
            emails = gmail.get_unread_emails(max_count)
            
            if not emails:
                return "📧 읽지 않은 이메일이 없습니다."
            
            response = f"📧 읽지 않은 이메일 ({len(emails)}개):\n\n"
            for email in emails:
                sender = email['from'].split('<')[0].strip()
                subject = email['subject'][:50]
                response += f"• **{sender}**\n  {subject}\n\n"
            
            return response
            
        except Exception as e:
            return f"📧 이메일 확인 오류: {str(e)}"


# 싱글톤 인스턴스
_agent = None

def get_agent() -> LLMAgent:
    """에이전트 싱글톤 반환"""
    global _agent
    if _agent is None:
        _agent = LLMAgent()
    return _agent

