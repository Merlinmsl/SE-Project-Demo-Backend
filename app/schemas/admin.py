from pydantic import BaseModel
from typing import Optional

class AdminLogin(BaseModel):
    username: str
    password: str

class AdminResponse(BaseModel):
    username: str
    display_name: Optional[str] = None
    token: str

class AdminLoginResponse(BaseModel):
    success: bool
    message: str
    admin: Optional[AdminResponse] = None
