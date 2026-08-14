from typing import Any


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="NOT_FOUND", status_code=404)


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="CONFLICT", status_code=409)


class InvalidImageError(AppError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "INVALID_IMAGE",
        status_code: int = 400,
    ) -> None:
        super().__init__(message, code=code, status_code=status_code)


class DifyError(AppError):
    def __init__(self, message: str, *, code: str = "DIFY_ERROR", details: Any = None) -> None:
        super().__init__(message, code=code, status_code=502, details=details)


class DifyTimeoutError(DifyError):
    def __init__(self) -> None:
        super().__init__("AI 分析超时，请稍后重试", code="DIFY_TIMEOUT")


class DifyOutputError(DifyError):
    def __init__(self, details: Any = None) -> None:
        super().__init__("AI 返回结果格式不符合约定", code="DIFY_OUTPUT_INVALID", details=details)


class DifyInterviewTimeoutError(DifyError):
    def __init__(self) -> None:
        super().__init__("AI 访谈超时，内容已保存", code="DIFY_INTERVIEW_TIMEOUT")


class DifyInterviewOutputError(DifyError):
    def __init__(self, details: Any = None) -> None:
        super().__init__(
            "AI 访谈返回结果格式不符合约定",
            code="DIFY_INTERVIEW_OUTPUT_INVALID",
            details=details,
        )
