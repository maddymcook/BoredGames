import uuid

from data5580_hw.models.base import LocalBaseModel
from pydantic import BaseModel, Field, EmailStr, model_validator


def get_id():
    return uuid.uuid4().hex

class User(BaseModel):
    name: str
    email: EmailStr
    id: str = Field(default_factory=get_id)


class UserUpdate(BaseModel):
    """Optional name and/or email for PATCH; at least one required."""
    name: str | None = None
    email: EmailStr | None = None

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.name is None and self.email is None:
            raise ValueError("At least one of name or email is required")
        return self
