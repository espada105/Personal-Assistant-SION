#!/bin/bash
# EC2 인스턴스에 서비스 배포 스크립트
# 사용법: ./deploy.sh [환경] [서비스]

set -e

# 설정
ENVIRONMENT=${1:-"production"}
TARGET_SERVICE=${2:-"all"}
AWS_REGION=${AWS_REGION:-"ap-northeast-2"}

# EC2 인스턴스 정보 (환경변수 또는 기본값)
EC2_HOST=${EC2_HOST:-""}
EC2_USER=${EC2_USER:-"ec2-user"}
EC2_KEY_PATH=${EC2_KEY_PATH:-"~/.ssh/sion-key.pem"}

# 색상 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# 사전 검사
check_prerequisites() {
    log_info "사전 검사 중..."
    
    if [ -z "${EC2_HOST}" ]; then
        log_error "EC2_HOST 환경변수가 설정되지 않았습니다."
        log_info "예: export EC2_HOST=ec2-xxx.compute.amazonaws.com"
        exit 1
    fi
    
    if [ ! -f "${EC2_KEY_PATH/#\~/$HOME}" ]; then
        log_error "SSH 키 파일을 찾을 수 없습니다: ${EC2_KEY_PATH}"
        exit 1
    fi
    
    log_info "EC2 호스트: ${EC2_HOST}"
    log_info "환경: ${ENVIRONMENT}"
}

# EC2에 SSH 명령 실행
ssh_exec() {
    local cmd=$1
    ssh -i "${EC2_KEY_PATH/#\~/$HOME}" \
        -o StrictHostKeyChecking=no \
        "${EC2_USER}@${EC2_HOST}" \
        "${cmd}"
}

# Docker Compose 파일 전송
upload_compose_file() {
    log_info "Docker Compose 파일 전송 중..."
    
    # 프로젝트 루트로 이동
    cd "$(dirname "$0")/../.."
    
    # 디렉토리 생성
    ssh_exec "mkdir -p ~/sion"
    
    # 파일 전송
    scp -i "${EC2_KEY_PATH/#\~/$HOME}" \
        -o StrictHostKeyChecking=no \
        docker-compose.yml \
        "${EC2_USER}@${EC2_HOST}:~/sion/"
    
    # 환경 변수 파일 전송 (있는 경우)
    if [ -f "configs/.env.${ENVIRONMENT}" ]; then
        scp -i "${EC2_KEY_PATH/#\~/$HOME}" \
            -o StrictHostKeyChecking=no \
            "configs/.env.${ENVIRONMENT}" \
            "${EC2_USER}@${EC2_HOST}:~/sion/.env"
    fi
}

# ECR에서 최신 이미지 풀
pull_images() {
    log_info "ECR에서 최신 이미지 풀 중..."
    
    local aws_account_id=$(aws sts get-caller-identity --query Account --output text)
    local ecr_registry="${aws_account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    
    # ECR 로그인
    ssh_exec "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ecr_registry}"
    
    # 이미지 풀
    local services=("asr" "nlu" "task-executor")
    
    for service in "${services[@]}"; do
        if [ "${TARGET_SERVICE}" = "all" ] || [ "${TARGET_SERVICE}" = "${service}" ]; then
            log_info "${service} 이미지 풀..."
            ssh_exec "docker pull ${ecr_registry}/sion-${service}:latest || true"
        fi
    done
}

# 서비스 배포
deploy_services() {
    log_info "서비스 배포 중..."
    
    cd ~/sion
    
    if [ "${TARGET_SERVICE}" = "all" ]; then
        # 모든 서비스 재시작
        ssh_exec "cd ~/sion && docker-compose pull && docker-compose up -d"
    else
        # 특정 서비스만 재시작
        ssh_exec "cd ~/sion && docker-compose pull ${TARGET_SERVICE} && docker-compose up -d ${TARGET_SERVICE}"
    fi
}

# 배포 상태 확인
check_deployment() {
    log_info "배포 상태 확인 중..."
    
    sleep 10  # 서비스 시작 대기
    
    ssh_exec "cd ~/sion && docker-compose ps"
    
    echo ""
    log_info "헬스 체크..."
    
    # 각 서비스 헬스 체크
    local services=("asr:8001" "nlu:8002" "task-executor:8003")
    
    for service_port in "${services[@]}"; do
        local service="${service_port%%:*}"
        local port="${service_port##*:}"
        
        if [ "${TARGET_SERVICE}" = "all" ] || [ "${TARGET_SERVICE}" = "${service}" ]; then
            local health_status=$(ssh_exec "curl -s -o /dev/null -w '%{http_code}' http://localhost:${port}/health || echo '000'")
            
            if [ "${health_status}" = "200" ]; then
                log_info "${service}: 정상 (HTTP ${health_status})"
            else
                log_warn "${service}: 비정상 (HTTP ${health_status})"
            fi
        fi
    done
}

# 롤백
rollback() {
    local version=$1
    
    if [ -z "${version}" ]; then
        log_error "롤백 버전을 지정해주세요."
        exit 1
    fi
    
    log_info "버전 ${version}으로 롤백 중..."
    
    local aws_account_id=$(aws sts get-caller-identity --query Account --output text)
    local ecr_registry="${aws_account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    
    # 특정 버전 이미지 풀 및 배포
    ssh_exec "cd ~/sion && \
        docker pull ${ecr_registry}/sion-${TARGET_SERVICE}:${version} && \
        docker-compose up -d ${TARGET_SERVICE}"
}

# 메인 실행
main() {
    echo "=========================================="
    echo "   SION EC2 배포 스크립트"
    echo "=========================================="
    echo ""
    
    check_prerequisites
    echo ""
    
    upload_compose_file
    echo ""
    
    pull_images
    echo ""
    
    deploy_services
    echo ""
    
    check_deployment
    echo ""
    
    log_info "배포 완료!"
}

# 스크립트 실행
main

