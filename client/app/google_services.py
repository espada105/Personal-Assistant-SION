"""
Google API Services
Gmail 및 Google Calendar 연동
"""

import os
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 프로젝트 루트 경로
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CREDENTIALS_PATH = os.path.join(PROJECT_ROOT, "configs", "google_credentials.json")
TOKEN_PATH = os.path.join(PROJECT_ROOT, "configs", "token.json")

# API 권한 범위
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
]


class GoogleAuthManager:
    """Google OAuth 인증 관리"""
    
    def __init__(self):
        self.creds = None
        self.load_credentials()
    
    def load_credentials(self):
        """저장된 토큰 로드"""
        if os.path.exists(TOKEN_PATH):
            with open(TOKEN_PATH, 'rb') as token:
                self.creds = pickle.load(token)
    
    def is_authenticated(self) -> bool:
        """인증 상태 확인"""
        return self.creds is not None and self.creds.valid
    
    def authenticate(self) -> bool:
        """Google OAuth 인증 수행"""
        try:
            # 토큰이 있고 갱신 토큰이 있는 경우 갱신 시도
            if self.creds and self.creds.refresh_token:
                try:
                    print("[GoogleAuth] 토큰 갱신 시도...")
                    self.creds.refresh(Request())
                    print("[GoogleAuth] 토큰 갱신 성공!")
                except Exception as refresh_error:
                    print(f"[GoogleAuth] 토큰 갱신 실패: {refresh_error}")
                    # 갱신 실패 시 새로운 인증 수행
                    self.creds = None
            
            # 토큰이 없으면 새로운 인증 수행
            if not self.creds or not self.creds.valid:
                if not os.path.exists(CREDENTIALS_PATH):
                    print(f"[GoogleAuth] credentials 파일을 찾을 수 없습니다: {CREDENTIALS_PATH}")
                    return False
                
                print("[GoogleAuth] 새로운 인증 수행...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            
            # 토큰 저장
            with open(TOKEN_PATH, 'wb') as token:
                pickle.dump(self.creds, token)
            
            print("[GoogleAuth] 인증 성공!")
            return True
            
        except Exception as e:
            print(f"[GoogleAuth] 인증 실패: {e}")
            return False
    
    def get_credentials(self):
        """인증 정보 반환"""
        if not self.is_authenticated():
            self.authenticate()
        return self.creds


class CalendarService:
    """Google Calendar 서비스"""
    
    def __init__(self, auth_manager: GoogleAuthManager):
        self.auth_manager = auth_manager
        self.service = None
    
    def connect(self) -> bool:
        """캘린더 서비스 연결"""
        try:
            creds = self.auth_manager.get_credentials()
            if creds:
                self.service = build('calendar', 'v3', credentials=creds)
                return True
            return False
        except Exception as e:
            print(f"[Calendar] 연결 실패: {e}")
            return False
    
    def get_today_events(self) -> List[Dict]:
        """오늘 일정 조회"""
        return self.get_events_for_date(datetime.now())
    
    def get_tomorrow_events(self) -> List[Dict]:
        """내일 일정 조회"""
        return self.get_events_for_date(datetime.now() + timedelta(days=1))
    
    def get_events_for_range(self, start_date: datetime, end_date: datetime, 
                              max_results: int = 50) -> List[Dict]:
        """날짜 범위의 일정 조회"""
        if not self.service:
            if not self.connect():
                return []
        
        try:
            # 시작일 00:00, 종료일 23:59 (로컬 시간대 사용)
            start_of_range = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_range = end_date.replace(hour=23, minute=59, second=59, microsecond=0)
            
            # 로컬 시간대 오프셋 계산 (한국: +09:00)
            import time
            utc_offset = -time.timezone if time.daylight == 0 else -time.altzone
            offset_hours = utc_offset // 3600
            offset_mins = (abs(utc_offset) % 3600) // 60
            tz_str = f"{offset_hours:+03d}:{offset_mins:02d}"
            
            # RFC3339 형식으로 시간대 포함
            time_min = start_of_range.strftime(f"%Y-%m-%dT%H:%M:%S{tz_str}")
            time_max = end_of_range.strftime(f"%Y-%m-%dT%H:%M:%S{tz_str}")
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            result = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                result.append({
                    'id': event['id'],
                    'title': event.get('summary', '(제목 없음)'),
                    'start': start,
                    'location': event.get('location', ''),
                    'description': event.get('description', '')
                })
            
            return result
            
        except Exception as e:
            print(f"[Calendar] 범위 일정 조회 실패: {e}")
            return []
    
    def get_events_for_date(self, date: datetime) -> List[Dict]:
        """특정 날짜 일정 조회"""
        if not self.service:
            if not self.connect():
                return []
        
        try:
            # 해당 날짜의 시작과 끝 (로컬 시간대 사용)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            # 로컬 시간대 오프셋 계산
            import time
            utc_offset = -time.timezone if time.daylight == 0 else -time.altzone
            offset_hours = utc_offset // 3600
            offset_mins = (abs(utc_offset) % 3600) // 60
            tz_str = f"{offset_hours:+03d}:{offset_mins:02d}"
            
            time_min = start_of_day.strftime(f"%Y-%m-%dT%H:%M:%S{tz_str}")
            time_max = end_of_day.strftime(f"%Y-%m-%dT%H:%M:%S{tz_str}")
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=20,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            result = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                result.append({
                    'id': event['id'],
                    'title': event.get('summary', '(제목 없음)'),
                    'start': start,
                    'location': event.get('location', ''),
                    'description': event.get('description', '')
                })
            
            return result
            
        except Exception as e:
            print(f"[Calendar] 일정 조회 실패: {e}")
            return []
    
    def create_event(self, title: str, start_time: datetime, 
                     duration_minutes: int = 60, location: str = "",
                     recurrence: str = None, recurrence_count: int = 10) -> Optional[Dict]:
        """일정 생성 (반복 일정 지원)"""
        if not self.service:
            if not self.connect():
                return None
        
        try:
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            event = {
                'summary': title,
                'location': location,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'Asia/Seoul',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Asia/Seoul',
                },
            }
            
            # 반복 규칙 추가
            if recurrence:
                rrule = self._build_recurrence_rule(recurrence, recurrence_count)
                if rrule:
                    event['recurrence'] = [rrule]
            
            created_event = self.service.events().insert(
                calendarId='primary', body=event
            ).execute()
            
            result = {
                'id': created_event['id'],
                'title': title,
                'start': start_time.isoformat(),
                'link': created_event.get('htmlLink', '')
            }
            
            if recurrence:
                result['recurrence'] = recurrence
            
            return result
            
        except Exception as e:
            print(f"[Calendar] 일정 생성 실패: {e}")
            return None
    
    def create_all_day_event(self, title: str, start_date: datetime, 
                              end_date: datetime = None, location: str = "",
                              recurrence: str = None, recurrence_count: int = 10) -> Optional[Dict]:
        """종일 일정 생성 (단일/기간/반복 지원)"""
        if not self.service:
            if not self.connect():
                return None
        
        try:
            # 종료 날짜가 없으면 하루 일정
            if end_date is None:
                end_date = start_date + timedelta(days=1)
            
            event = {
                'summary': title,
                'location': location,
                'start': {
                    'date': start_date.strftime('%Y-%m-%d'),  # 종일 이벤트는 date만 사용
                },
                'end': {
                    'date': end_date.strftime('%Y-%m-%d'),
                },
            }
            
            # 반복 규칙 추가
            if recurrence:
                rrule = self._build_recurrence_rule(recurrence, recurrence_count)
                if rrule:
                    event['recurrence'] = [rrule]
            
            created_event = self.service.events().insert(
                calendarId='primary', body=event
            ).execute()
            
            result = {
                'id': created_event['id'],
                'title': title,
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
                'link': created_event.get('htmlLink', '')
            }
            
            if recurrence:
                result['recurrence'] = recurrence
            
            return result
            
        except Exception as e:
            print(f"[Calendar] 종일 일정 생성 실패: {e}")
            return None
    
    def _build_recurrence_rule(self, recurrence: str, count: int = 10) -> Optional[str]:
        """반복 규칙(RRULE) 생성"""
        freq_map = {
            'yearly': 'YEARLY',
            'monthly': 'MONTHLY',
            'weekly': 'WEEKLY',
            'daily': 'DAILY'
        }
        
        freq = freq_map.get(recurrence.lower())
        if not freq:
            return None
        
        # COUNT로 반복 횟수 제한 (무한 반복 방지)
        return f"RRULE:FREQ={freq};COUNT={count}"
    
    def update_event(self, event_id: str, title: str = None, 
                     start_time: datetime = None, duration_minutes: int = None) -> Optional[Dict]:
        """일정 수정"""
        if not self.service:
            if not self.connect():
                return None
        
        try:
            # 기존 이벤트 조회
            event = self.service.events().get(
                calendarId='primary', eventId=event_id
            ).execute()
            
            # 수정할 내용 업데이트
            if title:
                event['summary'] = title
            
            if start_time:
                # 기존 duration 계산
                old_start = event['start'].get('dateTime')
                old_end = event['end'].get('dateTime')
                if old_start and old_end:
                    from dateutil import parser
                    old_duration = parser.parse(old_end) - parser.parse(old_start)
                    duration = duration_minutes if duration_minutes else int(old_duration.total_seconds() / 60)
                else:
                    duration = duration_minutes if duration_minutes else 60
                
                end_time = start_time + timedelta(minutes=duration)
                event['start'] = {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'Asia/Seoul',
                }
                event['end'] = {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Asia/Seoul',
                }
            
            updated_event = self.service.events().update(
                calendarId='primary', eventId=event_id, body=event
            ).execute()
            
            return {
                'id': updated_event['id'],
                'title': updated_event.get('summary', ''),
                'start': updated_event['start'].get('dateTime', ''),
                'link': updated_event.get('htmlLink', '')
            }
            
        except Exception as e:
            print(f"[Calendar] 일정 수정 실패: {e}")
            return None
    
    def delete_event(self, event_id: str) -> bool:
        """일정 삭제"""
        if not self.service:
            if not self.connect():
                return False
        
        try:
            self.service.events().delete(
                calendarId='primary', eventId=event_id
            ).execute()
            return True
            
        except Exception as e:
            print(f"[Calendar] 일정 삭제 실패: {e}")
            return False
    
    def search_events(self, query: str = None, search_date: datetime = None, 
                       max_results: int = 5) -> List[Dict]:
        """일정 검색 (제목 또는 날짜로)"""
        if not self.service:
            if not self.connect():
                return []
        
        try:
            # 날짜 범위 설정
            if search_date:
                # 특정 날짜 검색
                start_of_day = search_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = start_of_day + timedelta(days=1)
                time_min = start_of_day.isoformat() + 'Z'
                time_max = end_of_day.isoformat() + 'Z'
            else:
                # 오늘부터 한 달간 검색
                now = datetime.now()
                end_date = now + timedelta(days=30)
                time_min = now.isoformat() + 'Z'
                time_max = end_date.isoformat() + 'Z'
            
            # API 호출 파라미터
            params = {
                'calendarId': 'primary',
                'timeMin': time_min,
                'timeMax': time_max,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime',
            }
            
            # 검색어가 있으면 추가
            if query:
                params['q'] = query
            
            events_result = self.service.events().list(**params).execute()
            
            events = events_result.get('items', [])
            
            result = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                result.append({
                    'id': event['id'],
                    'title': event.get('summary', '(제목 없음)'),
                    'start': start,
                    'location': event.get('location', ''),
                })
            
            return result
            
        except Exception as e:
            print(f"[Calendar] 일정 검색 실패: {e}")
            return []


class GmailService:
    """Gmail 서비스"""
    
    def __init__(self, auth_manager: GoogleAuthManager):
        self.auth_manager = auth_manager
        self.service = None
    
    def connect(self) -> bool:
        """Gmail 서비스 연결"""
        try:
            creds = self.auth_manager.get_credentials()
            if creds:
                self.service = build('gmail', 'v1', credentials=creds)
                return True
            return False
        except Exception as e:
            print(f"[Gmail] 연결 실패: {e}")
            return False
    
    def get_unread_emails(self, max_results: int = 5) -> List[Dict]:
        """읽지 않은 이메일 조회"""
        if not self.service:
            if not self.connect():
                return []
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX', 'UNREAD'],
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            emails = []
            for msg in messages:
                msg_detail = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'From', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in msg_detail['payload']['headers']}
                
                emails.append({
                    'id': msg['id'],
                    'subject': headers.get('Subject', '(제목 없음)'),
                    'from': headers.get('From', ''),
                    'date': headers.get('Date', ''),
                    'snippet': msg_detail.get('snippet', '')[:100]
                })
            
            return emails
            
        except Exception as e:
            print(f"[Gmail] 이메일 조회 실패: {e}")
            return []
    
    def get_email_count(self) -> int:
        """읽지 않은 이메일 수 조회"""
        if not self.service:
            if not self.connect():
                return 0
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX', 'UNREAD']
            ).execute()
            
            return results.get('resultSizeEstimate', 0)
            
        except Exception as e:
            print(f"[Gmail] 이메일 수 조회 실패: {e}")
            return 0


# 전역 인스턴스
_auth_manager = None
_calendar_service = None
_gmail_service = None


def get_auth_manager() -> GoogleAuthManager:
    """인증 매니저 싱글톤"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = GoogleAuthManager()
    return _auth_manager


def get_calendar_service() -> CalendarService:
    """캘린더 서비스 싱글톤"""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = CalendarService(get_auth_manager())
    return _calendar_service


def get_gmail_service() -> GmailService:
    """Gmail 서비스 싱글톤"""
    global _gmail_service
    if _gmail_service is None:
        _gmail_service = GmailService(get_auth_manager())
    return _gmail_service

