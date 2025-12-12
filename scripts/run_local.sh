#!/bin/bash
# SION 로컬 개발 실행 스크립트
# 사용법: ./scripts/run_local.sh [서비스]

set -e

# 색상 출력
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

# 가상환경 활성화
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    log_warn "가상환경을 찾을 수 없습니다. ./scripts/setup_dev.sh를 먼저 실행하세요."
fi

# 환경 변수 로드
if [ -f "configs/.env" ]; then
    export $(cat configs/.env | grep -v '^#' | xargs)
fi

# 서비스 선택
SERVICE=${1:-"all"}

case $SERVICE in
    "asr")
        log_info "ASR 서비스 시작..."
        cd backend/asr
        uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
        ;;
    "nlu")
        log_info "NLU 서비스 시작..."
        cd backend/nlu
        uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
        ;;
    "task")
        log_info "Task Executor 서비스 시작..."
        cd backend/task_executor
        uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
        ;;
    "client")
        log_info "Python 클라이언트 시작..."
        cd client/python
        python main.py
        ;;
    "all")
        log_info "모든 서비스를 Docker Compose로 시작..."
        docker-compose up --build
        ;;
    *)
        echo "사용법: $0 [asr|nlu|task|client|all]"
        exit 1
        ;;
esac


