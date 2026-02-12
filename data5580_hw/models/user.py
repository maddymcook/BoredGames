import uuid


from data5580_hw.models.base import LocalBaseModel
from pydantic import EmailStr


# def get_id():
#     return uuid.uuid4().hex


class User(LocalBaseModel):
    name: str
    email: EmailStr

    # id: str = Field(default_factory=get_id)