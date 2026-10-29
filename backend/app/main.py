import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError


settings = get_settings()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next: Any):
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def error_body(request: Request, *, code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "data": None,
        "details": details,
        "request_id": getattr(request.state, "request_id", None),
    }


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(request, code=exc.code, message=exc.message, details=exc.details),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = exc.errors()
    for item in details:
        if "ctx" in item:
            item["ctx"] = {key: str(value) for key, value in item["ctx"].items()}
    return JSONResponse(
        status_code=422,
        content=error_body(
            request,
            code="VALIDATION_ERROR",
            message="请求参数校验失败",
            details=details,
        ),
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(request, code="HTTP_ERROR", message=str(exc.detail)),
        headers=exc.headers,
    )


app.include_router(api_router, prefix=settings.api_v1_prefix)
