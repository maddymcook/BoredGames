from pydantic import BaseModel, Field, EmailStr
import uuid

def get_id():
    return uuid.uuid4().hex

class User(BaseModel):
    name: str
    email: EmailStr

    id: str = Field(default_factory=get_id)