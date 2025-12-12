"""
Calendar Task Handler
Google Calendar API를 사용한 일정 작업
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from dateutil import parser as date_parser

from .base_task import BaseTask

logger = logging.getLogger(__name__)


class CalendarTask(BaseTask):
    """캘린더 작업 핸들러"""
    
    def __init__(self, credentials_path: Optional[str] = None):
        super().__init__()
        self.credentials_path = credentials_path
        self.service = None
        self._initialized = False
    
    def _init_service(self):
        """Google Calendar API 서비스 초기화"""
        if self._initialized:
            return
        
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            if not self.credentials_path:
                logger.warning("Google 인증 정보가 설정되지 않았습니다.")
                return
            
            creds = Credentials.from_authorized_user_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            
            self.service = build('calendar', 'v3', credentials=creds)
            self._initialized = True
            logger.info("Google Calendar 서비스 초기화 완료")
            
        except Exception as e:
            logger.error(f"Calendar 서비스 초기화 실패: {e}")
    
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        캘린더 작업 실행
        
        Actions:
            - check: 일정 확인
            - add: 일정 추가
            - delete: 일정 삭제
            - update: 일정 수정
        """
        self._init_service()
        
        if action == "check":
            return await self._check_events(params)
        elif action == "add":
            return await self._add_event(params)
        elif action == "delete":
            return await self._delete_event(params)
        elif action == "update":
            return await self._update_event(params)
        else:
            raise ValueError(f"지원하지 않는 액션: {action}")
    
    def _parse_date_entity(self, date_str: str) -> datetime:
        """날짜 엔티티 파싱"""
        today = datetime.now()
        date_str_lower = date_str.lower()
        
        if date_str_lower in ["오늘", "today"]:
            return today
        elif date_str_lower in ["내일", "tomorrow"]:
            return today + timedelta(days=1)
        elif date_str_lower in ["모레", "day after tomorrow"]:
            return today + timedelta(days=2)
        elif "다음 주" in date_str_lower or "next week" in date_str_lower:
            return today + timedelta(weeks=1)
        else:
            try:
                return date_parser.parse(date_str)
            except:
                return today
    
    def _parse_time_entity(self, time_str: str) -> tuple:
        """시간 엔티티 파싱 (hour, minute 반환)"""
        import re
        
        # 오전/오후 처리
        is_pm = "오후" in time_str or "pm" in time_str.lower()
        is_am = "오전" in time_str or "am" in time_str.lower()
        
        # 숫자 추출
        numbers = re.findall(r'\d+', time_str)
        
        if not numbers:
            return (9, 0)  # 기본값: 오전 9시
        
        hour = int(numbers[0])
        minute = int(numbers[1]) if len(numbers) > 1 else 0
        
        # 오전/오후 변환
        if is_pm and hour < 12:
            hour += 12
        elif is_am and hour == 12:
            hour = 0
        
        return (hour, minute)
    
    async def _check_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """일정 확인"""
        if not self.service:
            # 서비스 없으면 더미 데이터 반환
            return {
                "success": True,
                "message": "오늘 일정이 없습니다. (데모 모드)",
                "events": [],
                "count": 0
            }
        
        try:
            # 날짜 파싱
            date_str = params.get("date", "오늘")
            target_date = self._parse_date_entity(date_str)
            
            # 하루 범위 설정
            time_min = target_date.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
            time_max = target_date.replace(hour=23, minute=59, second=59).isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            event_list = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                event_list.append({
                    "id": event['id'],
                    "title": event.get('summary', '(제목 없음)'),
                    "start": start,
                    "location": event.get('location', ''),
                    "description": event.get('description', '')
                })
            
            return {
                "success": True,
                "message": f"{date_str} 일정: {len(event_list)}건",
                "events": event_list,
                "count": len(event_list)
            }
            
        except Exception as e:
            logger.error(f"일정 확인 오류: {e}")
            return {
                "success": False,
                "message": str(e),
                "events": []
            }
    
    async def _add_event(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """일정 추가"""
        if not self.service:
            return {
                "success": True,
                "message": "일정이 추가되었습니다. (데모 모드)",
                "event_id": "demo_event_id"
            }
        
        try:
            # 파라미터 파싱
            title = params.get("title", "새 일정")
            date_str = params.get("date", "오늘")
            time_str = params.get("time", "오전 9시")
            duration = params.get("duration", 60)  # 분 단위
            
            # 날짜/시간 파싱
            target_date = self._parse_date_entity(date_str)
            hour, minute = self._parse_time_entity(time_str)
            
            start_time = target_date.replace(hour=hour, minute=minute, second=0)
            end_time = start_time + timedelta(minutes=duration)
            
            event = {
                'summary': title,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'Asia/Seoul',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Asia/Seoul',
                },
            }
            
            # 위치, 설명 추가 (있는 경우)
            if params.get("location"):
                event["location"] = params["location"]
            if params.get("description"):
                event["description"] = params["description"]
            
            result = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            return {
                "success": True,
                "message": f"'{title}' 일정이 {date_str} {time_str}에 추가되었습니다.",
                "event_id": result['id'],
                "event_link": result.get('htmlLink', '')
            }
            
        except Exception as e:
            logger.error(f"일정 추가 오류: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    async def _delete_event(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """일정 삭제"""
        if not self.service:
            return {
                "success": True,
                "message": "일정이 삭제되었습니다. (데모 모드)"
            }
        
        try:
            event_id = params.get("event_id")
            
            if not event_id:
                # 제목으로 검색하여 삭제
                title = params.get("title", "")
                date_str = params.get("date", "오늘")
                
                # 일정 검색
                check_result = await self._check_events({"date": date_str})
                events = check_result.get("events", [])
                
                for event in events:
                    if title.lower() in event["title"].lower():
                        event_id = event["id"]
                        break
                
                if not event_id:
                    return {
                        "success": False,
                        "message": f"'{title}' 일정을 찾을 수 없습니다."
                    }
            
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            return {
                "success": True,
                "message": "일정이 삭제되었습니다.",
                "deleted_event_id": event_id
            }
            
        except Exception as e:
            logger.error(f"일정 삭제 오류: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    async def _update_event(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """일정 수정"""
        if not self.service:
            return {
                "success": True,
                "message": "일정이 수정되었습니다. (데모 모드)"
            }
        
        try:
            event_id = params.get("event_id")
            
            if not event_id:
                return {
                    "success": False,
                    "message": "수정할 일정 ID가 필요합니다."
                }
            
            # 기존 이벤트 조회
            event = self.service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            # 업데이트할 필드
            if params.get("title"):
                event["summary"] = params["title"]
            if params.get("location"):
                event["location"] = params["location"]
            if params.get("description"):
                event["description"] = params["description"]
            
            # 업데이트 실행
            updated_event = self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event
            ).execute()
            
            return {
                "success": True,
                "message": "일정이 수정되었습니다.",
                "event_id": updated_event['id']
            }
            
        except Exception as e:
            logger.error(f"일정 수정 오류: {e}")
            return {
                "success": False,
                "message": str(e)
            }


