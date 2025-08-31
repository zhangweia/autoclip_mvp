#!/bin/bash

# AutoClip MVP 开发环境启动脚本

echo "🚀 启动 AutoClip MVP 开发环境"

# 端口检查和清理函数
check_and_kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        echo "⚠️  端口$port已被占用，正在释放..."
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 2
        # 再次检查
        local remaining_pids=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$remaining_pids" ]; then
            echo "❌ 无法释放端口$port，请手动检查"
            return 1
        else
            echo "✅ 端口$port已释放"
        fi
    else
        echo "✅ 端口$port可用"
    fi
    return 0
}

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 检查Node.js环境
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装Node.js"
    exit 1
fi

# 安装后端依赖
echo "📦 检查后端依赖..."
if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate

# 检查是否需要安装依赖
# 如果requirements.txt比.venv_deps_installed新，或者.venv_deps_installed不存在，则重新安装
if [ ! -f ".venv_deps_installed" ] || [ "requirements.txt" -nt ".venv_deps_installed" ]; then
    echo "安装后端依赖..."
    pip install -r requirements.txt
    # 创建标记文件
    touch .venv_deps_installed
else
    echo "后端依赖已是最新，跳过安装"
fi

# 检查前端依赖
echo "📦 检查前端依赖..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi
cd ..

# 检查并清理端口
echo "🔍 检查端口是否可用..."
check_and_kill_port 8000  # 后端端口
check_and_kill_port 3000  # 前端端口

# 启动后端服务器
echo "🔧 启动后端API服务器（端口8000）..."
source venv/bin/activate
python backend_server.py &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端开发服务器，强制使用端口3000
echo "🎨 启动前端开发服务器（端口3000）..."
cd frontend
# 确保使用端口3000，添加host参数以便外部访问
VITE_PORT=3000 npm run dev -- --port 3000 --host 0.0.0.0 &
FRONTEND_PID=$!
cd ..

# 验证服务启动状态
echo "🔍 验证服务启动状态..."
sleep 2

# 检查后端是否启动成功
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ 后端服务启动成功"
else
    echo "⚠️  后端服务可能未完全启动，请稍等片刻"
fi

# 检查前端端口是否监听
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "✅ 前端服务启动成功"
else
    echo "⚠️  前端服务可能未完全启动，请稍等片刻"
fi

echo ""
echo "✅ 开发环境启动完成！"
echo "📱 前端地址: http://localhost:3000"
echo "🔌 后端API: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/docs"
echo ""
echo "💡 提示: 前端端口已锁定为3000，如遇端口冲突会自动清理"
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
trap 'echo "\n🛑 正在停止服务..."; kill $BACKEND_PID $FRONTEND_PID; exit' INT
wait