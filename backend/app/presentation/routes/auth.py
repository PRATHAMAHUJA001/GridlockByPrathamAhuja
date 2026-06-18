from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.data_access.database import get_db
from app.presentation.schemas.auth_schema import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.service.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        user = service.register(req.email, req.password, req.full_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    token = service.authenticate(req.email, req.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=token)
