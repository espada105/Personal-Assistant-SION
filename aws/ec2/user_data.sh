#!/bin/bash
# EC2 인스턴스 초기 설정 스크립트 (User Data)
# 새 EC2 인스턴스 생성 시 자동 실행됩니다.

set -e

# 로그 파일 설정
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "=========================================="
echo "SION EC2 인스턴스 초기 설정 시작"
echo "=========================================="

# 시스템 업데이트
echo "시스템 업데이트 중..."
yum update -y

# Docker 설치
echo "Docker 설치 중..."
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Docker Compose 설치
echo "Docker Compose 설치 중..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# AWS CLI v2 설치 (이미 설치되어 있을 수 있음)
echo "AWS CLI 확인 중..."
if ! command -v aws &> /dev/null; then
    echo "AWS CLI 설치 중..."
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    ./aws/install
    rm -rf awscliv2.zip aws/
fi

# 필수 유틸리티 설치
echo "필수 유틸리티 설치 중..."
yum install -y git curl htop

# SION 디렉토리 생성
echo "SION 디렉토리 생성..."
mkdir -p /home/ec2-user/sion
chown ec2-user:ec2-user /home/ec2-user/sion

# 로그 디렉토리 생성
mkdir -p /home/ec2-user/sion/logs/{asr,nlu,task_executor}
chown -R ec2-user:ec2-user /home/ec2-user/sion/logs

# 스왑 메모리 설정 (t2.micro 등 메모리가 적은 인스턴스용)
echo "스왑 메모리 설정..."
if [ ! -f /swapfile ]; then
    dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
fi

# Docker 로그 로테이션 설정
echo "Docker 로그 설정..."
cat > /etc/docker/daemon.json <<EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
EOF
systemctl restart docker

# 자동 시작 스크립트 생성
echo "자동 시작 스크립트 생성..."
cat > /home/ec2-user/start-sion.sh <<'EOF'
#!/bin/bash
cd /home/ec2-user/sion
docker-compose up -d
EOF
chmod +x /home/ec2-user/start-sion.sh
chown ec2-user:ec2-user /home/ec2-user/start-sion.sh

# systemd 서비스 등록
cat > /etc/systemd/system/sion.service <<EOF
[Unit]
Description=SION Personal Assistant Services
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=ec2-user
WorkingDirectory=/home/ec2-user/sion
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable sion.service

echo "=========================================="
echo "SION EC2 인스턴스 초기 설정 완료"
echo "=========================================="


