from datetime import datetime

from pydantic import Field, SecretStr, field_validator

from app.core.security import clean_display_name
from app.db.models import UserRole
from app.schemas.common import ORMModel


class DepartmentOption(ORMModel):
    id: str
    name: str


class RegistrationRequest(ORMModel):
    department_id: str = Field(min_length=32, max_length=32)
    name: str = Field(min_length=1, max_length=50)
    invitation_code: SecretStr

    @field_validator("name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        value = clean_display_name(value)
        if not value:
            raise ValueError("姓名不能为空")
        return value


class SessionCreateRequest(ORMModel):
    department_id: str = Field(min_length=32, max_length=32)
    name: str = Field(min_length=1, max_length=50)
    shared_password: SecretStr

    @field_validator("name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        value = clean_display_name(value)
        if not value:
            raise ValueError("姓名不能为空")
        return value


class CurrentUserRead(ORMModel):
    id: str
    department_id: str
    department_name: str
    name: str
    role: UserRole
    created_time: datetime


class AuthSessionRead(ORMModel):
    user: CurrentUserRead
    csrf_token: str
