from fastapi import APIRouter, Depends

from app.api.deps import require_authenticated_request
from app.api.routes import auth, health, interviews, organization, projects, requirements


api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
protected = [Depends(require_authenticated_request)]
api_router.include_router(
    projects.router, prefix="/projects", tags=["projects"], dependencies=protected
)
api_router.include_router(
    requirements.router,
    prefix="/requirements",
    tags=["requirements"],
    dependencies=protected,
)
api_router.include_router(
    interviews.router,
    prefix="/interviews",
    tags=["interviews"],
    dependencies=protected,
)
api_router.include_router(
    organization.departments_router, prefix="/departments", tags=["departments"]
)
api_router.include_router(
    organization.invitations_router, prefix="/invitations", tags=["invitations"]
)
api_router.include_router(organization.users_router, prefix="/users", tags=["users"])
