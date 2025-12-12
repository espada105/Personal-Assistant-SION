"""
AWS Lambda - Calendar Handler
일정 관리를 처리하는 Lambda 함수
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict

import boto3

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDB 테이블 (일정 저장용)
dynamodb = boto3.resource('dynamodb')
EVENTS_TABLE = os.environ.get('EVENTS_TABLE', 'sion-calendar-events')


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda 핸들러 함수
    
    Event 구조:
    {
        "action": "check" | "add" | "delete" | "update",
        "user_id": "user123",
        "params": {
            // action별 파라미터
        }
    }
    """
    logger.info(f"Event received: {json.dumps(event)}")
    
    try:
        action = event.get("action", "check")
        user_id = event.get("user_id", "default")
        params = event.get("params", {})
        
        if action == "check":
            result = check_events(user_id, params)
        elif action == "add":
            result = add_event(user_id, params)
        elif action == "delete":
            result = delete_event(user_id, params)
        elif action == "update":
            result = update_event(user_id, params)
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


def check_events(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    일정 확인
    """
    table = dynamodb.Table(EVENTS_TABLE)
    
    # 날짜 범위 설정
    date_str = params.get('date', 'today')
    
    if date_str == 'today':
        start_date = datetime.now().replace(hour=0, minute=0, second=0)
    elif date_str == 'tomorrow':
        start_date = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0)
    else:
        start_date = datetime.fromisoformat(date_str)
    
    end_date = start_date + timedelta(days=1)
    
    # DynamoDB 쿼리
    response = table.query(
        KeyConditionExpression='user_id = :uid AND start_time BETWEEN :start AND :end',
        ExpressionAttributeValues={
            ':uid': user_id,
            ':start': start_date.isoformat(),
            ':end': end_date.isoformat()
        }
    )
    
    events = response.get('Items', [])
    
    return {
        'date': start_date.strftime('%Y-%m-%d'),
        'count': len(events),
        'events': events
    }


def add_event(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    일정 추가
    """
    table = dynamodb.Table(EVENTS_TABLE)
    
    # 필수 파라미터 확인
    title = params.get('title', 'New Event')
    start_time = params.get('start_time')
    
    if not start_time:
        # 기본값: 오늘 오전 9시
        start_time = datetime.now().replace(hour=9, minute=0, second=0).isoformat()
    
    # 이벤트 ID 생성
    event_id = f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    
    # 종료 시간 (기본: 1시간)
    duration = params.get('duration', 60)
    end_time = (datetime.fromisoformat(start_time) + timedelta(minutes=duration)).isoformat()
    
    event = {
        'event_id': event_id,
        'user_id': user_id,
        'title': title,
        'start_time': start_time,
        'end_time': end_time,
        'location': params.get('location', ''),
        'description': params.get('description', ''),
        'created_at': datetime.now().isoformat()
    }
    
    table.put_item(Item=event)
    
    return {
        'event_id': event_id,
        'title': title,
        'start_time': start_time,
        'end_time': end_time,
        'status': 'created'
    }


def delete_event(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    일정 삭제
    """
    table = dynamodb.Table(EVENTS_TABLE)
    
    event_id = params.get('event_id')
    
    if not event_id:
        raise ValueError("event_id is required")
    
    table.delete_item(
        Key={
            'user_id': user_id,
            'event_id': event_id
        }
    )
    
    return {
        'event_id': event_id,
        'status': 'deleted'
    }


def update_event(user_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    일정 수정
    """
    table = dynamodb.Table(EVENTS_TABLE)
    
    event_id = params.get('event_id')
    
    if not event_id:
        raise ValueError("event_id is required")
    
    # 업데이트할 필드
    update_fields = []
    expression_values = {}
    
    if 'title' in params:
        update_fields.append('title = :title')
        expression_values[':title'] = params['title']
    
    if 'start_time' in params:
        update_fields.append('start_time = :start')
        expression_values[':start'] = params['start_time']
    
    if 'end_time' in params:
        update_fields.append('end_time = :end')
        expression_values[':end'] = params['end_time']
    
    if 'location' in params:
        update_fields.append('location = :loc')
        expression_values[':loc'] = params['location']
    
    if not update_fields:
        raise ValueError("No fields to update")
    
    table.update_item(
        Key={
            'user_id': user_id,
            'event_id': event_id
        },
        UpdateExpression='SET ' + ', '.join(update_fields),
        ExpressionAttributeValues=expression_values
    )
    
    return {
        'event_id': event_id,
        'status': 'updated'
    }


# 로컬 테스트용
if __name__ == "__main__":
    # 테스트 이벤트
    test_event = {
        "action": "check",
        "user_id": "test_user",
        "params": {
            "date": "today"
        }
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))


