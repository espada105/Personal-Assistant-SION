# SION API Reference

## 개요

SION 백엔드 서비스의 REST API 문서입니다.

**Base URL (로컬):**
- ASR: `http://localhost:8001`
- NLU: `http://localhost:8002`
- Task Executor: `http://localhost:8003`

**Base URL (AWS):**
- `https://api.sion.your-domain.com`

---

## ASR Service (음성 인식)

### 음성 인식

음성 파일을 텍스트로 변환합니다.

```
POST /transcribe
Content-Type: multipart/form-data
```

**Request:**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| audio | File | ✅ | WAV 형식 오디오 파일 |

**Response:**

```json
{
  "text": "안녕하세요. 오늘 일정을 알려주세요.",
  "language": "ko",
  "duration": 3.5,
  "confidence": 0.95,
  "segments": [
    {
      "start": 0.0,
      "end": 1.5,
      "text": "안녕하세요."
    },
    {
      "start": 1.5,
      "end": 3.5,
      "text": "오늘 일정을 알려주세요."
    }
  ]
}
```

### 헬스 체크

```
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "service": "asr",
  "model_loaded": true
}
```

---

## NLU Service (자연어 이해)

### 텍스트 분석

텍스트에서 의도와 엔티티를 추출합니다.

```
POST /analyze
Content-Type: application/json
```

**Request:**

```json
{
  "text": "내일 오후 3시에 회의 일정 잡아줘"
}
```

**Response:**

```json
{
  "text": "내일 오후 3시에 회의 일정 잡아줘",
  "intent": {
    "name": "schedule_add",
    "confidence": 0.92
  },
  "entities": [
    {
      "type": "date",
      "value": "내일",
      "start": 0,
      "end": 2
    },
    {
      "type": "time",
      "value": "오후 3시",
      "start": 3,
      "end": 8
    }
  ]
}
```

### 의도만 분류

```
POST /classify
Content-Type: application/json
```

**Request:**

```json
{
  "text": "오늘 일정 알려줘"
}
```

**Response:**

```json
{
  "text": "오늘 일정 알려줘",
  "intent": "schedule_check",
  "confidence": 0.89
}
```

### 지원 의도 목록

```
GET /intents
```

**Response:**

```json
{
  "intents": {
    "schedule_check": "일정 확인",
    "schedule_add": "일정 추가",
    "schedule_delete": "일정 삭제",
    "email_check": "이메일 확인",
    "email_send": "이메일 전송",
    "llm_chat": "일반 대화/질문",
    ...
  }
}
```

---

## Task Executor Service (작업 실행)

### 작업 실행

NLU 결과를 바탕으로 작업을 실행합니다.

```
POST /execute
Content-Type: application/json
```

**Request:**

```json
{
  "intent": "schedule_add",
  "entities": {
    "date": "내일",
    "time": "오후 3시",
    "title": "회의"
  }
}
```

**Response:**

```json
{
  "success": true,
  "intent": "schedule_add",
  "action": "add",
  "result": {
    "event_id": "abc123xyz",
    "title": "회의",
    "start_time": "2024-01-15T15:00:00",
    "end_time": "2024-01-15T16:00:00"
  },
  "message": "작업이 성공적으로 완료되었습니다."
}
```

### LLM 대화

OpenAI를 통한 대화를 수행합니다.

```
POST /chat
Content-Type: application/json
```

**Request:**

```json
{
  "message": "파이썬에서 리스트와 튜플의 차이점은?",
  "conversation_id": null
}
```

**Response:**

```json
{
  "message": "파이썬에서 리스트와 튜플의 주요 차이점은...",
  "conversation_id": "conv_abc123",
  "tokens_used": 150
}
```

### 지원 작업 목록

```
GET /tasks
```

**Response:**

```json
{
  "tasks": [
    "schedule_check",
    "schedule_add",
    "schedule_delete",
    "email_check",
    "email_send",
    "llm_chat",
    "web_search"
  ],
  "handlers": ["email", "calendar", "llm"]
}
```

---

## 에러 응답

모든 API는 에러 발생 시 다음 형식으로 응답합니다:

```json
{
  "detail": "에러 메시지"
}
```

### HTTP 상태 코드

| 코드 | 설명 |
|------|------|
| 200 | 성공 |
| 400 | 잘못된 요청 |
| 401 | 인증 실패 |
| 404 | 리소스 없음 |
| 500 | 서버 내부 오류 |
| 503 | 서비스 불가 (모델 미로드 등) |

---

## 인증

AWS 배포 환경에서는 API Gateway를 통해 인증이 필요합니다.

```
Authorization: Bearer <API_KEY>
```

---

## Rate Limiting

- 개발 환경: 제한 없음
- 프로덕션: 분당 60 요청

---

## SDK 예시

### Python

```python
import httpx

async def transcribe_audio(audio_path: str) -> dict:
    async with httpx.AsyncClient() as client:
        with open(audio_path, 'rb') as f:
            files = {'audio': f}
            response = await client.post(
                'http://localhost:8001/transcribe',
                files=files
            )
        return response.json()

async def analyze_text(text: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'http://localhost:8002/analyze',
            json={'text': text}
        )
        return response.json()
```

### cURL

```bash
# ASR
curl -X POST http://localhost:8001/transcribe \
  -F "audio=@audio.wav"

# NLU
curl -X POST http://localhost:8002/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "오늘 일정 알려줘"}'

# Task Executor
curl -X POST http://localhost:8003/execute \
  -H "Content-Type: application/json" \
  -d '{"intent": "schedule_check", "entities": {"date": "오늘"}}'
```


