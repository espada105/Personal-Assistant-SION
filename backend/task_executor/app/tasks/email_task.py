"""
Email Task Handler
Gmail API를 사용한 이메일 작업
"""

import logging
from typing import Any, Dict, Optional

from .base_task import BaseTask

logger = logging.getLogger(__name__)


class EmailTask(BaseTask):
    """이메일 작업 핸들러"""
    
    def __init__(self, credentials_path: Optional[str] = None):
        super().__init__()
        self.credentials_path = credentials_path
        self.service = None
        self._initialized = False
    
    def _init_service(self):
        """Gmail API 서비스 초기화"""
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
                scopes=['https://www.googleapis.com/auth/gmail.readonly',
                       'https://www.googleapis.com/auth/gmail.send']
            )
            
            self.service = build('gmail', 'v1', credentials=creds)
            self._initialized = True
            logger.info("Gmail 서비스 초기화 완료")
            
        except Exception as e:
            logger.error(f"Gmail 서비스 초기화 실패: {e}")
    
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        이메일 작업 실행
        
        Actions:
            - check: 새 이메일 확인
            - send: 이메일 전송
            - search: 이메일 검색
        """
        self._init_service()
        
        if action == "check":
            return await self._check_emails(params)
        elif action == "send":
            return await self._send_email(params)
        elif action == "search":
            return await self._search_emails(params)
        else:
            raise ValueError(f"지원하지 않는 액션: {action}")
    
    async def _check_emails(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """새 이메일 확인"""
        if not self.service:
            return {
                "success": False,
                "message": "Gmail 서비스가 초기화되지 않았습니다.",
                "emails": []
            }
        
        try:
            max_results = params.get("max_results", 5)
            
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX', 'UNREAD'],
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg in messages:
                msg_data = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'From', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
                
                emails.append({
                    "id": msg['id'],
                    "subject": headers.get('Subject', '(제목 없음)'),
                    "from": headers.get('From', ''),
                    "date": headers.get('Date', ''),
                    "snippet": msg_data.get('snippet', '')
                })
            
            return {
                "success": True,
                "message": f"{len(emails)}개의 새 이메일이 있습니다.",
                "emails": emails,
                "count": len(emails)
            }
            
        except Exception as e:
            logger.error(f"이메일 확인 오류: {e}")
            return {
                "success": False,
                "message": str(e),
                "emails": []
            }
    
    async def _send_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """이메일 전송"""
        if not self.service:
            return {
                "success": False,
                "message": "Gmail 서비스가 초기화되지 않았습니다."
            }
        
        try:
            import base64
            from email.mime.text import MIMEText
            
            self.validate_params(params, ["to", "subject", "body"])
            
            message = MIMEText(params["body"])
            message['to'] = params["to"]
            message['subject'] = params["subject"]
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            return {
                "success": True,
                "message": f"이메일이 {params['to']}에게 전송되었습니다.",
                "message_id": result['id']
            }
            
        except Exception as e:
            logger.error(f"이메일 전송 오류: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    async def _search_emails(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """이메일 검색"""
        if not self.service:
            return {
                "success": False,
                "message": "Gmail 서비스가 초기화되지 않았습니다.",
                "emails": []
            }
        
        try:
            query = params.get("query", "")
            max_results = params.get("max_results", 10)
            
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            return {
                "success": True,
                "message": f"'{query}' 검색 결과: {len(messages)}건",
                "emails": [{"id": m['id']} for m in messages],
                "count": len(messages)
            }
            
        except Exception as e:
            logger.error(f"이메일 검색 오류: {e}")
            return {
                "success": False,
                "message": str(e),
                "emails": []
            }


