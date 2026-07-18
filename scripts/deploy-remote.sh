#!/bin/bash
# 远程部署脚本 - 小猪教学工具箱

set -e

# 部署配置
# 请修改以下配置为你的服务器信息
REMOTE_HOST="YOUR_SERVER_IP"       # 你的服务器 IP
REMOTE_USER="YOUR_SERVER_USER"     # SSH 用户名（如 root）
REMOTE_DIR="/home/www/agent"       # 部署目录
PROJECT_NAME="video-generator"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}开始部署 小猪教学工具箱${NC}"
echo -e "${GREEN}======================================${NC}"

# 检查配置
if [ "$REMOTE_HOST" = "YOUR_SERVER_IP" ]; then
    echo -e "${RED}请先修改脚本中的 REMOTE_HOST 为你的服务器 IP${NC}"
    exit 1
fi

# 检查 SSH 密钥
if [ ! -f ~/.ssh/id_rsa ] && [ ! -f ~/.ssh/id_ed25519 ]; then
    echo -e "${YELLOW}未找到 SSH 密钥，正在生成...${NC}"
    ssh-keygen -t ed25519 -C "deploy@video-generator" -f ~/.ssh/id_ed25519 -N ""
    echo -e "${YELLOW}请将以下公钥添加到远程服务器的 ~/.ssh/authorized_keys：${NC}"
    cat ~/.ssh/id_ed25519.pub
    echo -e "${YELLOW}或执行命令：ssh-copy-id ${REMOTE_USER}@${REMOTE_HOST}${NC}"
    exit 1
fi

# 1. 同步代码到远程服务器
echo -e "\n${GREEN}[1/4] 正在同步代码到远程服务器...${NC}"
rsync -avz --progress \
    --exclude='.git' \
    --exclude='.idea' \
    --exclude='.vscode' \
    --exclude='.kiro' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='.DS_Store' \
    --exclude='node_modules' \
    --exclude='frontend/dist' \
    --exclude='projects/*' \
    --exclude='character_library/*' \
    --exclude='*.log' \
    --exclude='deploy-remote.sh' \
    ./ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/

if [ $? -ne 0 ]; then
    echo -e "${RED}代码同步失败！${NC}"
    exit 1
fi
echo -e "${GREEN}代码同步完成！${NC}"

# 2. 修正文件权限
echo -e "\n${GREEN}[2/4] 正在修正文件权限...${NC}"
ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} << ENDSSH
cd ${REMOTE_DIR}

# 修正文件所有者
chown -R root:root ${REMOTE_DIR}

# 设置目录权限 755
find ${REMOTE_DIR} -type d -exec chmod 755 {} \;

# 设置文件权限 644
find ${REMOTE_DIR} -type f -exec chmod 644 {} \;

# 脚本需要执行权限
chmod +x ${REMOTE_DIR}/scripts/*.sh

# 数据目录需要写权限
mkdir -p ${REMOTE_DIR}/projects ${REMOTE_DIR}/character_library
chmod -R 777 ${REMOTE_DIR}/projects ${REMOTE_DIR}/character_library

echo "文件权限修正完成！"
ENDSSH

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}权限修正出现警告，继续部署...${NC}"
fi

# 3. 重新构建并启动容器
echo -e "\n${GREEN}[3/4] 正在重新构建并启动容器...${NC}"
ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} << ENDSSH
cd ${REMOTE_DIR}

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "未找到 .env 文件，从模板创建..."
    cp .env.docker .env
    echo "请编辑 .env 文件配置 API 密钥等信息"
fi

# 重新构建镜像
echo "正在构建镜像..."
docker compose build

# 重启服务
echo "正在重启服务..."
docker compose down
docker compose up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查 MySQL 是否就绪
echo "等待 MySQL 就绪..."
for i in {1..30}; do
    if docker compose exec -T mysql mysqladmin ping -h localhost --silent 2>/dev/null; then
        echo "MySQL 已就绪"
        break
    fi
    echo "等待 MySQL... (\$i/30)"
    sleep 2
done

echo "容器启动完成！"
ENDSSH

if [ $? -ne 0 ]; then
    echo -e "${RED}服务启动失败！${NC}"
    exit 1
fi

# 4. 检查部署结果
echo -e "\n${GREEN}[4/4] 检查部署结果...${NC}"
ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} << ENDSSH
cd ${REMOTE_DIR}

echo "容器状态："
docker compose ps

echo -e "\n后端日志（最后 10 行）："
docker compose logs --tail 10 backend

echo -e "\n前端日志（最后 5 行）："
docker compose logs --tail 5 frontend
ENDSSH

echo -e "\n${GREEN}======================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}======================================${NC}"
echo -e "${YELLOW}前端地址：http://${REMOTE_HOST}${NC}"
echo -e "${YELLOW}后端 API：http://${REMOTE_HOST}:8000${NC}"
echo -e "${YELLOW}API 文档：http://${REMOTE_HOST}:8000/docs${NC}"
