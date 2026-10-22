from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.auth.user import User
from app.models.employee import Employee
from app.schemas.auth.auth import (
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.security.dependencies import get_current_user
from app.security.security import (
    create_access_token,
    hash_password,
    verify_password,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Register a new OrbitHR user."""

    existing_user = (
        db.query(User)
        .filter(User.email == request.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    employee = (
        db.query(Employee)
        .filter(Employee.employee_id == request.employee_id)
        .first()
    )

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    existing_employee_user = (
        db.query(User)
        .filter(User.employee_id == request.employee_id)
        .first()
    )

    if existing_employee_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This employee is already linked to a user account",
        )

    new_user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        employee_id=request.employee_id,
        role="EMPLOYEE",
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(
        user_id=new_user.id,
        employee_id=new_user.employee_id,
        role=new_user.role,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate a user and return a JWT access token."""

    user = (
        db.query(User)
        .filter(User.email == request.email)
        .first()
    )

    if not user or not verify_password(
        request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(
        user_id=user.id,
        employee_id=user.employee_id,
        role=user.role,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    """Return the currently authenticated user."""

    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        employee_id=current_user.employee_id,
        role=current_user.role,
        is_active=current_user.is_active,
    )