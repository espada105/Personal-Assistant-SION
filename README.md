# 🤖 Personal Assistant SION

Docker와 AWS를 활용한 AI 기반 개인 비서 시스템

## 📋 프로젝트 개요

로컬 데스크톱 앱(GUI, Hotkey)과 클라우드 기반 AI 서비스를 결합한 개인 비서 시스템입니다.
- **로컬**: C++ Hotkey 모듈, Python GUI 클라이언트
- **클라우드**: ASR(음성인식), NLU(자연어이해), Task Execution 서비스

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                         로컬 PC (Client)                            │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ C++ Hotkey   │───▶│ Python       │───▶│ 로컬 Task Execution  │  │
│  │ Module       │    │ Client       │    │ (파일 탐색 등)        │  │
│  └──────────────┘    └──────┬───────┘    └──────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────────┘
                              │ REST API
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                    │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐ │
│  │ API Gateway │───▶│ EC2/ECS     │───▶│ Task Executor           │ │
│  └─────────────┘    │ (ASR + NLU) │    │ (Email, Calendar, LLM)  │ │
│                     └─────────────┘    └─────────────────────────┘ │
│                            │                                        │
│                     ┌──────▼──────┐                                 │
│                     │ S3 (Logs,   │                                 │
│                     │ Models)     │                                 │
│                     └─────────────┘                                 │
└─────────────────────────────────────────────────────────────────────┘
```

## 📁 프로젝트 구조

```
Personal-Assistant-SION/
├── client/                 # 로컬 PC 클라이언트
│   ├── python/            # Python 클라이언트 (음성 녹음, API 호출)
│   └── cpp/               # C++ Hotkey 모듈
├── backend/               # 백엔드 마이크로서비스
│   ├── asr/              # ASR (음성 인식) 서비스
│   ├── nlu/              # NLU (자연어 이해) 서비스
│   └── task_executor/    # Task Execution 서비스
├── aws/                   # AWS 배포 관련
│   ├── ecr/              # ECR 이미지 푸시 스크립트
│   ├── ec2/              # EC2 배포 스크립트
│   ├── lambda/           # Lambda 함수
│   └── cloudformation/   # IaC 템플릿
├── configs/              # 설정 파일
├── scripts/              # 유틸리티 스크립트
├── tests/                # 테스트 코드
└── docs/                 # 문서
```

## 🚀 시작하기

### 사전 요구사항

- Python 3.10+
- Docker & Docker Compose
- AWS CLI (배포 시)
- CMake 3.20+ (C++ 모듈 빌드 시)

### 로컬 개발 환경 설정

```bash
# 저장소 클론
git clone https://github.com/your-username/Personal-Assistant-SION.git
cd Personal-Assistant-SION

# Python 가상환경 설정
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp configs/.env.example configs/.env
# configs/.env 파일을 수정하여 필요한 값 입력
```

### Docker로 백엔드 서비스 실행

```bash
# 모든 서비스 빌드 및 실행
docker-compose up --build

# 개별 서비스 실행
docker-compose up asr-service
docker-compose up nlu-service
docker-compose up task-executor
```

### AWS 배포

```bash
# ECR에 이미지 푸시
./aws/ecr/push_images.sh

# EC2에 배포
./aws/ec2/deploy.sh
```

## 🛠️ 기술 스택

| 영역 | 기술 |
|------|------|
| **클라이언트** | Python, C++, PyQt/Tkinter |
| **백엔드** | FastAPI, Python |
| **AI/ML** | Whisper (ASR), Transformers (NLU) |
| **컨테이너** | Docker, Docker Compose |
| **클라우드** | AWS (EC2, ECR, S3, Lambda, API Gateway) |
| **IaC** | AWS CloudFormation |

## 📊 주요 기능

- 🎤 **음성 인식 (ASR)**: Whisper 모델 기반 한국어 음성 인식
- 🧠 **의도 분류 (NLU)**: 사용자 발화 의도 및 엔티티 추출
- 📧 **이메일 관리**: Gmail API 연동 이메일 확인/발송
- 📅 **일정 관리**: Google Calendar API 연동
- 💬 **LLM 질의**: OpenAI API를 통한 자연어 대화
- 📁 **파일 탐색**: 로컬 파일 시스템 탐색 및 관리

## 📝 라이선스

MIT License

## 👤 Author

SION Project Team

