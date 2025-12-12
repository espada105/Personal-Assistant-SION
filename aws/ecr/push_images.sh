#!/bin/bash
# ECR에 Docker 이미지 푸시 스크립트
# 사용법: ./push_images.sh [서비스명]

set -e

# 설정
AWS_REGION=${AWS_REGION:-"ap-northeast-2"}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
PROJECT_NAME="sion"

# 색상 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ECR 로그인
ecr_login() {
    log_info "ECR에 로그인 중..."
    aws ecr get-login-password --region ${AWS_REGION} | \
        docker login --username AWS --password-stdin ${ECR_REGISTRY}
}

# ECR 리포지토리 생성 (없는 경우)
create_repository() {
    local repo_name=$1
    
    if ! aws ecr describe-repositories --repository-names "${repo_name}" --region ${AWS_REGION} > /dev/null 2>&1; then
        log_info "ECR 리포지토리 생성: ${repo_name}"
        aws ecr create-repository \
            --repository-name "${repo_name}" \
            --region ${AWS_REGION} \
            --image-scanning-configuration scanOnPush=true
    else
        log_info "ECR 리포지토리 존재: ${repo_name}"
    fi
}

# 이미지 빌드 및 푸시
build_and_push() {
    local service=$1
    local context_path=$2
    local repo_name="${PROJECT_NAME}-${service}"
    local image_tag="${ECR_REGISTRY}/${repo_name}:latest"
    local version_tag="${ECR_REGISTRY}/${repo_name}:$(date +%Y%m%d-%H%M%S)"
    
    log_info "===== ${service} 서비스 빌드 시작 ====="
    
    # 리포지토리 생성
    create_repository "${repo_name}"
    
    # Docker 이미지 빌드
    log_info "Docker 이미지 빌드: ${repo_name}"
    docker build -t "${repo_name}" "${context_path}"
    
    # 태그 지정
    docker tag "${repo_name}" "${image_tag}"
    docker tag "${repo_name}" "${version_tag}"
    
    # 푸시
    log_info "ECR에 푸시: ${image_tag}"
    docker push "${image_tag}"
    docker push "${version_tag}"
    
    log_info "===== ${service} 서비스 푸시 완료 ====="
    echo ""
}

# 메인 실행
main() {
    local target_service=$1
    
    # 프로젝트 루트로 이동
    cd "$(dirname "$0")/../.."
    
    log_info "AWS 계정 ID: ${AWS_ACCOUNT_ID}"
    log_info "AWS 리전: ${AWS_REGION}"
    log_info "ECR 레지스트리: ${ECR_REGISTRY}"
    echo ""
    
    # ECR 로그인
    ecr_login
    echo ""
    
    # 서비스별 빌드
    if [ -z "${target_service}" ] || [ "${target_service}" = "all" ]; then
        # 모든 서비스 빌드
        build_and_push "asr" "./backend/asr"
        build_and_push "nlu" "./backend/nlu"
        build_and_push "task-executor" "./backend/task_executor"
    else
        # 특정 서비스만 빌드
        case "${target_service}" in
            "asr")
                build_and_push "asr" "./backend/asr"
                ;;
            "nlu")
                build_and_push "nlu" "./backend/nlu"
                ;;
            "task-executor"|"task_executor")
                build_and_push "task-executor" "./backend/task_executor"
                ;;
            *)
                log_error "알 수 없는 서비스: ${target_service}"
                log_info "사용 가능한 서비스: asr, nlu, task-executor, all"
                exit 1
                ;;
        esac
    fi
    
    log_info "모든 이미지 푸시 완료!"
}

# 스크립트 실행
main "$@"


