from fastapi import APIRouter

from app.api.routes import health, interviews, organization, projects, requirements


api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(requirements.router, prefix="/requirements", tags=["requirements"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["interviews"])
api_router.include_router(
    organization.departments_router, prefix="/departments", tags=["departments"]
)
api_router.include_router(
    organization.invitations_router, prefix="/invitations", tags=["invitations"]
)
