#!/bin/bash
# 开发环境启动脚本
# 同时启动后端和前端

echo "🚀 启动开发环境..."

# 启动后端
echo "📦 启动后端服务 (端口 8000)..."
python3 -m uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 等待后端启动
sleep 2

# 启动前端
echo "🎨 启动前端服务 (端口 5173)..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ 服务已启动:"
echo "   后端: http://localhost:8000"
echo "   前端: http://localhost:5173"
echo "   API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获 Ctrl+C 信号
trap "echo '正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

# 等待子进程
wait
