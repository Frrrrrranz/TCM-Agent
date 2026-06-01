from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.chat import router as chat_router

# 初始化日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="TCM-Agent Web Gateway",
    description="中医药智能 Agent 的可视化网关后端，基于 WebSocket 转发 Agent 通信",
    version="1.0.0"
)

# 注册 CORS 跨域资源共享中间件，为前端开发模式调试提供支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载聊天路由
app.include_router(chat_router)

@app.get("/health")
async def health_check() -> dict[str, str]:
    """健康检查接口。"""
    return {"status": "ok", "message": "TCM-Agent web gateway is active"}
