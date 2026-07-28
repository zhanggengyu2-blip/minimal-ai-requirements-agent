from fastapi import APIRouter, Request

from app.schemas.common import ApiResponse


router = APIRouter()


@router.get("/health", response_model=ApiResponse[dict[str, str]])
def health(request: Request) -> ApiResponse[dict[str, str]]:
    return ApiResponse(data={"status": "ok"}, request_id=request.state.request_id)

