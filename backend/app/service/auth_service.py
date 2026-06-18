from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.data_access.models import User
from app.data_access.repositories.user_repo import UserRepository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def register(self, email: str, password: str, full_name: str | None = None) -> User:
        existing = self.repo.get_by_email(email)
        if existing:
            raise ValueError("Email already registered")
        user = User(
            email=email,
            password_hash=pwd_context.hash(password),
            full_name=full_name,
        )
        return self.repo.create(user)

    def authenticate(self, email: str, password: str) -> str | None:
        user = self.repo.get_by_email(email)
        if not user or not pwd_context.verify(password, user.password_hash):
            return None
        return self._create_token(user.id)

    def get_user_from_token(self, token: str) -> User | None:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if not user_id:
                return None
            return self.repo.get_by_id(user_id)
        except Exception:
            return None

    def _create_token(self, user_id: str) -> str:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return jwt.encode({"sub": user_id, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
