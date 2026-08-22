# ===== TCM-Agent 完整后端部署 =====
# 包含：FastAPI WebSocket 网关 + Node.js AI 引擎
# 构建镜像后，运行即可同时提供后端服务和 AI 对话能力
#
# 使用方式：
#   docker build -t tcm-agent-backend .
#   docker run -p 8000:8000 \
#     -e ANTHROPIC_API_KEY=your_key_here \
#     tcm-agent-backend

FROM python:3.12-slim

# 安装 Node.js 20
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- 1. 安装 Node.js AI 引擎（TCM-Agent） ----
COPY package.json package-lock.json ./
COPY tsconfig.json ./
COPY src/ ./src/
COPY bin/ ./bin/
COPY external/ ./external/
COPY docs/ ./docs/

RUN npm install

# ---- 2. 安装 Python WebSocket 网关（FastAPI） ----
COPY tcm-mcp-server/pyproject.toml ./tcm-mcp-server/
RUN cd tcm-mcp-server && pip install -e .

COPY tcm-mcp-server/src/ ./tcm-mcp-server/src/

# ---- 3. 准备数据目录 ----
RUN mkdir -p /app/tcm-mcp-server/data

# ---- 4. 暴露端口并启动 ----
EXPOSE 8000

# agent_service.py 会从 Python 代码动态定位 Node.js 项目目录
# ANTHROPIC_API_KEY 等环境变量由 docker run -e 传入
CMD ["uvicorn", "tcm_mcp_server.web.main:app", "--host", "0.0.0.0", "--port", "8000"]