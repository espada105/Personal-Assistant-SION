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
            "description": "일정을 확인합니다. 다양한 기간 표현 지원: 오늘/내일/모레, 이번주/다음주/저번주, 이번달/다음달/저번달, 특정 월(12월, 2024년 1월), 날짜 범위 등",
            "parameters": {
                "type": "object",
                "properties": {
                    "period_type": {
                        "type": "string",
                        "description": "조회 유형: 'day'(특정일), 'week'(주), 'month'(월), 'range'(범위)",
                        "enum": ["day", "week", "month", "range"]
                    },
                    "relative": {
                        "type": "string",
                        "description": "상대 표현: 'current'(이번), 'next'(다음), 'previous'(저번/지난). day의 경우 'today', 'tomorrow', 'day_after'(모레)",
                        "enum": ["current", "next", "previous", "today", "tomorrow", "day_after"]
                    },
                    "year": {
                        "type": "integer",
                        "description": "연도 (예: 2024, 2025). 생략시 현재 연도"
                    },
                    "month": {
                        "type": "integer",
                        "description": "월 (1-12). period_type이 'month'일 때 특정 월 지정"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "시작 날짜 (YYYY-MM-DD). period_type이 'range'나 'day'일 때 사용"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "종료 날짜 (YYYY-MM-DD). period_type이 'range'일 때 사용"
                    }
                },
                "required": ["period_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_calendar_event",
            "description": "새로운 일정을 추가합니다. 단일/여러날/반복 일정 모두 지원. 예: '내일 3시에 회의', '12/11부터 12/13까지 출장', '매년 12월 25일 크리스마스', '매월 1일 월급날', '매주 월요일 팀미팅'",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "일정 제목"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "시작 날짜. 'today', 'tomorrow', 또는 'YYYY-MM-DD' 형식 (예: '2024-12-11')"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "종료 날짜 (여러 날 일정인 경우). 'YYYY-MM-DD' 형식. 하루 일정이면 생략"
                    },
                    "time": {
                        "type": "string",
                        "description": "시작 시간. 'HH:MM' 24시간 형식 (예: '15:00'). 종일 일정이면 생략"
                    },
                    "duration": {
                        "type": "integer",
                        "description": "일정 길이 (분 단위). 기본값 60. 종일 일정이면 생략",
                        "default": 60
                    },
                    "is_all_day": {
                        "type": "boolean",
                        "description": "종일 일정 여부. 기간 일정(여러 날)은 보통 종일 일정",
                        "default": False
                    },
                    "recurrence": {
                        "type": "string",
                        "description": "반복 주기. 'yearly'(매년), 'monthly'(매월), 'weekly'(매주), 'daily'(매일). 반복 일정이 아니면 생략",
                        "enum": ["yearly", "monthly", "weekly", "daily"]
                    },
                    "recurrence_count": {
                        "type": "integer",
                        "description": "반복 횟수. 생략하면 무한 반복 (10년치)",
                        "default": 10
                    }
                },
                "required": ["title", "start_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_calendar_event",
            "description": "기존 일정을 수정합니다. 예: '3시 회의를 4시로 변경해줘', '내일 미팅 제목 바꿔줘'",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_query": {
                        "type": "string",
                        "description": "수정할 일정을 찾기 위한 검색어 (일정 제목). 없으면 날짜로만 검색"
                    },
                    "search_date": {
                        "type": "string",
                        "description": "수정할 일정의 날짜. 'YYYY-MM-DD' 형식. 특정 날짜 일정 수정 시 사용"
                    },
                    "new_title": {
                        "type": "string",
                        "description": "새로운 일정 제목 (변경할 경우)"
                    },
                    "new_date": {
                        "type": "string",
                        "description": "새로운 날짜. 'YYYY-MM-DD' 형식"
                    },
                    "new_time": {
                        "type": "string",
                        "description": "새로운 시간. 'HH:MM' 24시간 형식 (예: '16:00')"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_calendar_event",
            "description": "일정을 삭제/취소합니다. 제목이나 날짜로 검색 가능. 예: '내일 일정 삭제해줘', '회의 취소해줘', '12월 15일 미팅 삭제'",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_query": {
                        "type": "string",
                        "description": "삭제할 일정 제목 (검색어). 없으면 날짜의 모든 일정 표시"
                    },
                    "search_date": {
                        "type": "string",
                        "description": "삭제할 일정 날짜. 'YYYY-MM-DD' 형식. 예: '2024-12-15'"
                    }
                },
                "required": []
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
def get_system_prompt() -> str:
    """현재 날짜/시간 정보를 포함한 시스템 프롬프트 생성"""
    now = datetime.now()
    weekdays = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
    weekday = weekdays[now.weekday()]
    
    return f"""당신은 SION이라는 친절한 개인 비서 AI입니다.

## 현재 시간 정보
- 오늘 날짜: {now.strftime('%Y년 %m월 %d일')} ({weekday})
- 현재 시간: {now.strftime('%H시 %M분')}
- 현재 연도: {now.year}년
- 현재 월: {now.month}월

## 사용 가능한 기능
1. 일정 확인 (check_calendar) - 다양한 기간의 일정 조회
2. 일정 추가 (add_calendar_event) - 새로운 일정 추가
3. 일정 수정 (update_calendar_event) - 기존 일정 수정
4. 일정 삭제 (delete_calendar_event) - 일정 삭제
5. 이메일 확인 (check_email) - 읽지 않은 이메일 확인

## 일정 확인 (check_calendar) 사용법

### 필수 파라미터: period_type
- "day": 특정 하루 (오늘, 내일, 모레, 어제, 특정 날짜)
- "week": 주 단위 (이번주, 다음주, 저번주)
- "month": 월 단위 (이번달, 다음달, 저번달, 특정 월)
- "range": 날짜 범위 (시작일~종료일)

### relative 파라미터 (상대 표현)
- "current": 이번 (이번주, 이번달)
- "next": 다음 (다음주, 다음달, 내일)
- "previous": 저번/지난 (저번주, 저번달, 어제)
- "today": 오늘
- "tomorrow": 내일
- "day_after": 모레

### 예시 매핑
- "오늘 일정" → period_type="day", relative="today"
- "내일 일정" → period_type="day", relative="tomorrow"
- "이번주 일정" → period_type="week", relative="current"
- "다음주 일정" → period_type="week", relative="next"
- "저번주 일정" → period_type="week", relative="previous"
- "이번달 일정" → period_type="month", relative="current"
- "다음달 일정" → period_type="month", relative="next"
- "12월 일정" → period_type="month", month=12, year={now.year}
- "24년 12월 일정" → period_type="month", month=12, year=2024
- "2024년 1월 일정" → period_type="month", month=1, year=2024

## 날짜 처리 규칙
- "오늘" = {now.strftime('%Y-%m-%d')}
- "내일" = {(now + timedelta(days=1)).strftime('%Y-%m-%d')}
- "모레" = {(now + timedelta(days=2)).strftime('%Y-%m-%d')}
- "XX년"이라고 하면 20XX년으로 해석 (예: 24년 = 2024년, 25년 = 2025년)
- 연도 없이 "12월"이라고 하면 현재 연도({now.year}년) 기준

## 반복 일정 추가 (add_calendar_event)
- "매년" → recurrence="yearly" (예: 매년 12월 25일 크리스마스)
- "매월" → recurrence="monthly" (예: 매월 1일 월급날)
- "매주" → recurrence="weekly" (예: 매주 월요일 팀미팅)
- "매일" → recurrence="daily" (예: 매일 아침 운동)
- recurrence_count는 반복 횟수 (기본 10회)

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
                    {"role": "system", "content": get_system_prompt()},
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
        """일정 확인 (다양한 기간 지원)"""
        if not GOOGLE_AVAILABLE:
            return "📅 Google 캘린더가 연결되지 않았습니다.\n\n'Google 로그인' 버튼을 클릭해주세요."
        
        try:
            calendar = get_calendar_service()
            now = datetime.now()
            
            period_type = args.get("period_type", "day")
            relative = args.get("relative", "current")
            year = args.get("year", now.year)
            month = args.get("month")
            start_date_str = args.get("start_date")
            end_date_str = args.get("end_date")
            
            # === 날짜 범위 결정 ===
            
            if period_type == "day":
                # 특정 일
                if start_date_str:
                    try:
                        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                    except:
                        start_date = now
                    date_label = start_date.strftime('%Y-%m-%d')
                elif relative == "today" or relative == "current":
                    start_date = now
                    date_label = "오늘"
                elif relative == "tomorrow" or relative == "next":
                    start_date = now + timedelta(days=1)
                    date_label = "내일"
                elif relative == "day_after":
                    start_date = now + timedelta(days=2)
                    date_label = "모레"
                elif relative == "previous":
                    start_date = now - timedelta(days=1)
                    date_label = "어제"
                else:
                    start_date = now
                    date_label = "오늘"
                end_date = start_date
                
            elif period_type == "week":
                # 주 단위
                days_since_monday = now.weekday()
                
                if relative == "current":
                    start_date = now - timedelta(days=days_since_monday)
                    date_label = "이번 주"
                elif relative == "next":
                    start_date = now - timedelta(days=days_since_monday) + timedelta(weeks=1)
                    date_label = "다음 주"
                elif relative == "previous":
                    start_date = now - timedelta(days=days_since_monday) - timedelta(weeks=1)
                    date_label = "저번 주"
                else:
                    start_date = now - timedelta(days=days_since_monday)
                    date_label = "이번 주"
                
                end_date = start_date + timedelta(days=6)
                date_label += f" ({start_date.strftime('%m/%d')}~{end_date.strftime('%m/%d')})"
                
            elif period_type == "month":
                # 월 단위
                target_year = year
                
                if month:
                    # 특정 월 지정 (예: 12월, 2024년 1월)
                    target_month = month
                    date_label = f"{target_year}년 {target_month}월"
                elif relative == "current":
                    target_month = now.month
                    target_year = now.year
                    date_label = "이번 달"
                elif relative == "next":
                    if now.month == 12:
                        target_month = 1
                        target_year = now.year + 1
                    else:
                        target_month = now.month + 1
                        target_year = now.year
                    date_label = "다음 달"
                elif relative == "previous":
                    if now.month == 1:
                        target_month = 12
                        target_year = now.year - 1
                    else:
                        target_month = now.month - 1
                        target_year = now.year
                    date_label = "저번 달"
                else:
                    target_month = now.month
                    target_year = now.year
                    date_label = "이번 달"
                
                # 월의 시작과 끝
                start_date = datetime(target_year, target_month, 1)
                if target_month == 12:
                    end_date = datetime(target_year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(target_year, target_month + 1, 1) - timedelta(days=1)
                
                date_label += f" ({start_date.strftime('%Y-%m-%d')}~{end_date.strftime('%Y-%m-%d')})"
                
            elif period_type == "range":
                # 범위 지정
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else now
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else start_date
                except:
                    start_date = now
                    end_date = now
                date_label = f"{start_date.strftime('%m/%d')} ~ {end_date.strftime('%m/%d')}"
            
            else:
                start_date = now
                end_date = now
                date_label = "오늘"
            
            # === 일정 조회 ===
            if start_date.date() == end_date.date():
                events = calendar.get_events_for_date(start_date)
            else:
                events = calendar.get_events_for_range(start_date, end_date)
            
            if not events:
                return f"📅 {date_label} 일정이 없습니다."
            
            response = f"📅 {date_label} 일정 ({len(events)}개):\n\n"
            
            current_date = None
            for event in events:
                event_start = event['start']
                
                # 날짜와 시간 분리
                if 'T' in event_start:
                    event_date = event_start.split('T')[0]
                    event_time = event_start.split('T')[1][:5]
                else:
                    event_date = event_start
                    event_time = "종일"
                
                # 날짜가 바뀌면 헤더 추가 (기간 조회 시)
                if start_date.date() != end_date.date() and event_date != current_date:
                    current_date = event_date
                    response += f"\n📆 {event_date}\n"
                
                response += f"  • {event_time} - {event['title']}\n"
            
            return response
            
        except Exception as e:
            return f"📅 일정 확인 오류: {str(e)}"
    
    def _add_calendar_event(self, args: Dict[str, Any]) -> str:
        """일정 추가 (단일/기간/반복 일정 지원)"""
        if not GOOGLE_AVAILABLE:
            return "📅 Google 캘린더가 연결되지 않았습니다."
        
        try:
            calendar = get_calendar_service()
            
            title = args.get("title", "새 일정")
            start_date_str = args.get("start_date", args.get("date", "today"))
            end_date_str = args.get("end_date")
            time_str = args.get("time")
            duration = args.get("duration", 60)
            is_all_day = args.get("is_all_day", False)
            recurrence = args.get("recurrence")  # yearly, monthly, weekly, daily
            recurrence_count = args.get("recurrence_count", 10)
            
            # 시작 날짜 파싱
            start_date = self._parse_date(start_date_str)
            
            # 반복 주기 한글 매핑
            recurrence_labels = {
                'yearly': '매년',
                'monthly': '매월',
                'weekly': '매주',
                'daily': '매일'
            }
            recurrence_label = recurrence_labels.get(recurrence, '')
            
            # 종료 날짜가 있으면 기간 일정 (종일 일정으로 처리)
            if end_date_str:
                end_date = self._parse_date(end_date_str)
                # 종료 날짜는 다음 날까지 포함 (Google Calendar 종일 이벤트 특성)
                end_date = end_date + timedelta(days=1)
                
                result = calendar.create_all_day_event(
                    title, start_date, end_date, 
                    recurrence=recurrence, recurrence_count=recurrence_count
                )
                
                if result:
                    msg = f"✅ 일정이 추가되었습니다!\n\n📅 {title}\n📆 {start_date.strftime('%Y-%m-%d')} ~ {(end_date - timedelta(days=1)).strftime('%Y-%m-%d')}"
                    if recurrence:
                        msg += f"\n🔁 {recurrence_label} 반복 ({recurrence_count}회)"
                    return msg
                else:
                    return "❌ 일정 추가에 실패했습니다."
            
            # 종일 일정
            elif is_all_day or not time_str:
                result = calendar.create_all_day_event(
                    title, start_date,
                    recurrence=recurrence, recurrence_count=recurrence_count
                )
                
                if result:
                    msg = f"✅ 일정이 추가되었습니다!\n\n📅 {title}\n📆 {start_date.strftime('%Y-%m-%d')} (종일)"
                    if recurrence:
                        msg += f"\n🔁 {recurrence_label} 반복 ({recurrence_count}회)"
                    return msg
                else:
                    return "❌ 일정 추가에 실패했습니다."
            
            # 시간 지정 일정
            else:
                try:
                    hour, minute = map(int, time_str.split(":"))
                except:
                    hour, minute = 9, 0
                
                start_time = start_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                result = calendar.create_event(
                    title, start_time, duration,
                    recurrence=recurrence, recurrence_count=recurrence_count
                )
                
                if result:
                    msg = f"✅ 일정이 추가되었습니다!\n\n📅 {title}\n🕐 {start_time.strftime('%Y-%m-%d %H:%M')}"
                    if recurrence:
                        msg += f"\n🔁 {recurrence_label} 반복 ({recurrence_count}회)"
                    return msg
                else:
                    return "❌ 일정 추가에 실패했습니다."
            
        except Exception as e:
            return f"📅 일정 추가 오류: {str(e)}"
    
    def _parse_date(self, date_str: str) -> datetime:
        """날짜 문자열 파싱"""
        if not date_str:
            return datetime.now()
        
        date_str = date_str.lower().strip()
        
        if date_str == "today":
            return datetime.now()
        elif date_str == "tomorrow":
            return datetime.now() + timedelta(days=1)
        else:
            # 다양한 형식 시도
            formats = [
                "%Y-%m-%d",      # 2024-12-11
                "%Y/%m/%d",      # 2024/12/11
                "%m/%d",         # 12/11
                "%m-%d",         # 12-11
                "%d일",          # 11일
            ]
            
            for fmt in formats:
                try:
                    parsed = datetime.strptime(date_str, fmt)
                    # 연도가 없으면 현재 연도 사용
                    if parsed.year == 1900:
                        parsed = parsed.replace(year=datetime.now().year)
                    return parsed
                except:
                    continue
            
            # 파싱 실패시 현재 날짜
            return datetime.now()
    
    def _update_calendar_event(self, args: Dict[str, Any]) -> str:
        """일정 수정 (제목 또는 날짜로 검색)"""
        if not GOOGLE_AVAILABLE:
            return "📅 Google 캘린더가 연결되지 않았습니다."
        
        try:
            calendar = get_calendar_service()
            search_query = args.get("search_query")
            search_date_str = args.get("search_date")
            
            # 검색 날짜 파싱
            search_date = None
            if search_date_str:
                search_date = self._parse_date(search_date_str)
            
            # 일정 검색
            events = calendar.search_events(
                query=search_query,
                search_date=search_date,
                max_results=5
            )
            
            if not events:
                if search_date:
                    return f"📅 {search_date.strftime('%Y-%m-%d')}에 일정이 없습니다."
                elif search_query:
                    return f"📅 '{search_query}' 일정을 찾을 수 없습니다."
                else:
                    return "📅 수정할 일정 정보를 입력해주세요."
            
            # 여러 개면 목록 표시
            if len(events) > 1 and not search_query:
                response = f"📅 수정 가능한 일정 ({len(events)}개):\n\n"
                for i, evt in enumerate(events, 1):
                    response += f"{i}. {evt['title']} ({evt['start']})\n"
                response += "\n수정할 일정 제목을 말씀해주세요."
                return response
            
            event = events[0]
            event_id = event['id']
            
            # 새로운 시간 파싱
            new_time = None
            new_date = args.get("new_date")
            new_time_str = args.get("new_time")
            
            if new_date or new_time_str:
                # 날짜 파싱
                if new_date:
                    event_date = self._parse_date(new_date)
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
        """일정 삭제 (제목 또는 날짜로 검색)"""
        if not GOOGLE_AVAILABLE:
            return "📅 Google 캘린더가 연결되지 않았습니다."
        
        try:
            calendar = get_calendar_service()
            search_query = args.get("search_query")
            search_date_str = args.get("search_date")
            
            # 날짜 파싱
            search_date = None
            if search_date_str:
                search_date = self._parse_date(search_date_str)
            
            # 일정 검색
            events = calendar.search_events(
                query=search_query, 
                search_date=search_date, 
                max_results=5
            )
            
            if not events:
                if search_date:
                    return f"📅 {search_date.strftime('%Y-%m-%d')}에 일정이 없습니다."
                elif search_query:
                    return f"📅 '{search_query}' 일정을 찾을 수 없습니다."
                else:
                    return "📅 검색할 일정 정보를 입력해주세요."
            
            # 여러 개면 목록 표시 (첫 번째 삭제)
            if len(events) > 1 and not search_query:
                response = f"📅 {search_date.strftime('%Y-%m-%d')}의 일정 ({len(events)}개):\n\n"
                for i, evt in enumerate(events, 1):
                    response += f"{i}. {evt['title']} ({evt['start']})\n"
                response += "\n삭제할 일정 제목을 말씀해주세요."
                return response
            
            # 삭제 실행
            event = events[0]
            event_id = event['id']
            event_title = event['title']
            event_start = event['start']
            
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

