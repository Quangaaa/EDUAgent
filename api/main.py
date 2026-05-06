import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from model.factory import warmup_models

from api.db import init_db
from api.response import build_error, build_success
from api.routers.auth import router as auth_router
from api.routers.chat import router as chat_router
from api.routers.knowledgebase import router as knowledgebase_router
from api.service import get_init_status
from utils.log import logger


def _load_cors_origins() -> list[str]:
	raw = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
	if not raw:
		# 开发默认白名单
		return ["http://localhost:5173", "http://127.0.0.1:5173"]

	origins = [item.strip() for item in raw.split(",") if item.strip()]
	return origins


def _load_cors_allow_credentials() -> bool:
	raw = os.getenv("CORS_ALLOW_CREDENTIALS", "true").strip().lower()
	return raw in {"1", "true", "yes", "on"}


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""应用启动与关闭生命周期。"""
	try:
		init_db()
		logger.info("[api] sqlite 数据库初始化完成")
	except Exception as exc:
		logger.error(f"[api] 数据库初始化失败: {exc}")
		raise

	model_status = warmup_models(raise_on_error=False)
	if model_status["chat_model_error"] or model_status["embedding_model_error"]:
		logger.warning(f"[api] 模型预热异常: {model_status}")
	else:
		logger.info("[api] 模型预热完成")

	yield

	logger.info("[api] 服务已关闭")


app = FastAPI(
	title="Edu Agent API",
	version="0.1.0",
	description="教育对话/智能体/规划统一后端服务",
	lifespan=lifespan,
)

cors_origins = _load_cors_origins()
cors_allow_credentials = _load_cors_allow_credentials()

logger.info(
	f"[api] CORS 配置: allow_origins={cors_origins}, allow_credentials={cors_allow_credentials}"
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=cors_origins,
	allow_credentials=cors_allow_credentials,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
	request.state.request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
	response = await call_next(request)
	response.headers["X-Request-Id"] = request.state.request_id
	return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
	payload = build_error(
		message=str(exc.detail),
		code=exc.status_code,
		request_id=getattr(request.state, "request_id", None),
	)
	return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	payload = build_error(
		message="Request validation failed",
		code=422,
		request_id=getattr(request.state, "request_id", None),
		details=exc.errors(),
	)
	return JSONResponse(status_code=422, content=payload)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
	logger.error(f"[api] unhandled exception: {exc}")
	payload = build_error(
		message="Internal server error",
		code=500,
		request_id=getattr(request.state, "request_id", None),
	)
	return JSONResponse(status_code=500, content=payload)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(knowledgebase_router)


@app.get("/")
def root():
	return build_success({"service": "edu-agent-api", "version": "0.1.0"})


@app.get("/health")
def health():
	return build_success({"status": "healthy"})


@app.get("/status")
def status():
	return build_success({"services": get_init_status()})


if __name__ == "__main__":
	import uvicorn

	uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

