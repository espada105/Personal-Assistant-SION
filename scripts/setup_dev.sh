#!/bin/bash
# SION 개발 환경 설정 스크립트
# 사용법: ./scripts/setup_dev.sh

set -e

# 색상 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

echo "=========================================="
echo "   SION Personal Assistant"
echo "   개발 환경 설정"
echo "=========================================="
echo ""

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)
log_info "프로젝트 루트: ${PROJECT_ROOT}"

# Python 버전 확인
log_step "Python 버전 확인..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    log_info "Python: ${PYTHON_VERSION}"
else
    log_error "Python3가 설치되어 있지 않습니다."
    exit 1
fi

# 가상환경 생성
log_step "Python 가상환경 생성..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    log_info "가상환경 생성 완료: ./venv"
else
    log_warn "가상환경이 이미 존재합니다."
fi

# 가상환경 활성화
log_step "가상환경 활성화..."
source venv/bin/activate
log_info "가상환경 활성화 완료"

# pip 업그레이드
log_step "pip 업그레이드..."
pip install --upgrade pip

# 의존성 설치
log_step "Python 의존성 설치..."
pip install -r requirements.txt
log_info "루트 의존성 설치 완료"

# 개발 도구 설치
log_step "개발 도구 설치..."
pip install black isort flake8 mypy pytest pytest-asyncio pytest-cov

# 환경 변수 파일 생성
log_step "환경 변수 파일 설정..."
if [ ! -f "configs/.env" ]; then
    cp configs/.env.example configs/.env
    log_info ".env 파일 생성 완료"
    log_warn "configs/.env 파일을 수정하여 실제 값을 입력하세요!"
else
    log_warn ".env 파일이 이미 존재합니다."
fi

# Docker 확인
log_step "Docker 확인..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    log_info "Docker: ${DOCKER_VERSION}"
else
    log_warn "Docker가 설치되어 있지 않습니다. Docker 기능을 사용하려면 설치하세요."
fi

# Docker Compose 확인
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    log_info "Docker Compose: ${COMPOSE_VERSION}"
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version)
    log_info "Docker Compose (plugin): ${COMPOSE_VERSION}"
else
    log_warn "Docker Compose가 설치되어 있지 않습니다."
fi

# AWS CLI 확인
log_step "AWS CLI 확인..."
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version)
    log_info "AWS CLI: ${AWS_VERSION}"
else
    log_warn "AWS CLI가 설치되어 있지 않습니다. AWS 기능을 사용하려면 설치하세요."
fi

# 디렉토리 생성
log_step "필요한 디렉토리 생성..."
mkdir -p logs
mkdir -p backend/asr/models
mkdir -p backend/nlu/models
log_info "디렉토리 생성 완료"

# pre-commit 설정 (선택사항)
log_step "pre-commit 설정..."
if [ -f ".pre-commit-config.yaml" ]; then
    pip install pre-commit
    pre-commit install
    log_info "pre-commit 설치 완료"
fi

echo ""
echo "=========================================="
echo "   설정 완료!"
echo "=========================================="
echo ""
echo "다음 단계:"
echo "  1. configs/.env 파일을 수정하여 API 키 등을 설정하세요"
echo "  2. 가상환경 활성화: source venv/bin/activate"
echo "  3. 로컬 실행: ./scripts/run_local.sh"
echo "  4. Docker 실행: docker-compose up --build"
echo ""

