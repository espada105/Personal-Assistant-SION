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
            # 토큰이 만료되었으면 갱신
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                # 새로운 인증 수행
                if not os.path.exists(CREDENTIALS_PATH):
                    print(f"[GoogleAuth] credentials 파일을 찾을 수 없습니다: {CREDENTIALS_PATH}")
                    return False
                
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
    
    def get_events_for_date(self, date: datetime) -> List[Dict]:
        """특정 날짜 일정 조회"""
        if not self.service:
            if not self.connect():
                return []
        
        try:
            # 해당 날짜의 시작과 끝
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                maxResults=10,
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
                     duration_minutes: int = 60, location: str = "") -> Optional[Dict]:
        """일정 생성"""
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
            
            created_event = self.service.events().insert(
                calendarId='primary', body=event
            ).execute()
            
            return {
                'id': created_event['id'],
                'title': title,
                'start': start_time.isoformat(),
                'link': created_event.get('htmlLink', '')
            }
            
        except Exception as e:
            print(f"[Calendar] 일정 생성 실패: {e}")
            return None


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

