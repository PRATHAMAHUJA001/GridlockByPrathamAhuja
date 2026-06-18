from datetime import datetime

from sqlalchemy.orm import Session

from app.data_access.models import Violation
from app.data_access.repositories.violation_repo import ViolationRepository


class ViolationService:
    def __init__(self, db: Session):
        self.repo = ViolationRepository(db)

    def list_violations(
        self,
        violation_type: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Violation], int]:
        return self.repo.list_violations(violation_type, severity, status, date_from, date_to, page, limit)

    def get_violation(self, violation_id: str) -> Violation | None:
        return self.repo.get_by_id(violation_id)

    def update_status(self, violation_id: str, status: str, reviewed_by: str | None = None) -> Violation | None:
        return self.repo.update_status(violation_id, status, reviewed_by)
