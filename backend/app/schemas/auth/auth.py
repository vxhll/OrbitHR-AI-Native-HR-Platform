from pydantic import BaseModel, EmailStr, Field



class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    employee_id: str = Field(min_length=1, max_length=20)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    id: int
    email: str
    employee_id: str
    role: str
    is_active: bool