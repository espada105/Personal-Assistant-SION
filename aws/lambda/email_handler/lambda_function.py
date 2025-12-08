"""
AWS Lambda - Email Handler
이메일 확인/전송을 처리하는 Lambda 함수
"""

import json
import logging
import os
from typing import Any, Dict

import boto3

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda 핸들러 함수
    
    Event 구조:
    {
        "action": "check" | "send" | "search",
        "params": {
            // action별 파라미터
        }
    }
    """
    logger.info(f"Event received: {json.dumps(event)}")
    
    try:
        action = event.get("action", "check")
        params = event.get("params", {})
        
        if action == "check":
            result = check_emails(params)
        elif action == "send":
            result = send_email(params)
        elif action == "search":
            result = search_emails(params)
        else:
            raise ValueError(f"Unknown action: {action}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "result": result
            })
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }


def check_emails(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    새 이메일 확인
    
    참고: 실제 Gmail API 연동을 위해서는
    Google OAuth 인증이 필요합니다.
    여기서는 SES를 통한 수신 이메일 확인 예시를 보여줍니다.
    """
    # S3에서 수신된 이메일 확인 (SES + S3 수신 규칙 설정 필요)
    s3 = boto3.client('s3')
    bucket_name = os.environ.get('EMAIL_BUCKET', 'sion-emails')
    
    try:
        response = s3.list_objects_v2(
            Bucket=bucket_name,
            Prefix='incoming/',
            MaxKeys=10
        )
        
        emails = []
        for obj in response.get('Contents', []):
            emails.append({
                'key': obj['Key'],
                'date': obj['LastModified'].isoformat(),
                'size': obj['Size']
            })
        
        return {
            'count': len(emails),
            'emails': emails
        }
        
    except Exception as e:
        logger.error(f"S3 access error: {e}")
        return {
            'count': 0,
            'emails': [],
            'error': str(e)
        }


def send_email(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    이메일 전송 (AWS SES 사용)
    """
    ses = boto3.client('ses')
    
    to_address = params.get('to')
    subject = params.get('subject', 'No Subject')
    body = params.get('body', '')
    
    if not to_address:
        raise ValueError("'to' address is required")
    
    sender = os.environ.get('SENDER_EMAIL', 'noreply@example.com')
    
    response = ses.send_email(
        Source=sender,
        Destination={
            'ToAddresses': [to_address]
        },
        Message={
            'Subject': {'Data': subject},
            'Body': {
                'Text': {'Data': body}
            }
        }
    )
    
    return {
        'message_id': response['MessageId'],
        'status': 'sent'
    }


def search_emails(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    이메일 검색
    """
    query = params.get('query', '')
    
    # 실제 구현에서는 Elasticsearch나 DynamoDB를 사용하여
    # 인덱싱된 이메일을 검색합니다.
    
    return {
        'query': query,
        'results': [],
        'message': 'Search not implemented yet'
    }


# 로컬 테스트용
if __name__ == "__main__":
    # 테스트 이벤트
    test_event = {
        "action": "check",
        "params": {}
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))

