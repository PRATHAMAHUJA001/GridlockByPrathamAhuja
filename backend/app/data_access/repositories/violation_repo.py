from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.data_access.models import Violation


class ViolationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, violation: Violation) -> Violation:
        self.db.add(violation)
        self.db.commit()
        self.db.refresh(violation)
        return violation

    def get_by_id(self, violation_id: str) -> Violation | None:
        return (
            self.db.query(Violation)
            .options(joinedload(Violation.vehicle), joinedload(Violation.original_image), joinedload(Violation.evidence_image))
            .filter(Violation.id == violation_id)
            .first()
        )

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
        q = self.db.query(Violation).options(joinedload(Violation.vehicle))
        if violation_type:
            q = q.filter(Violation.violation_type == violation_type)
        if severity:
            q = q.filter(Violation.severity == severity)
        if status:
            q = q.filter(Violation.status == status)
        if date_from:
            q = q.filter(Violation.detected_at >= date_from)
        if date_to:
            q = q.filter(Violation.detected_at <= date_to)
        total = q.count()
        items = q.order_by(Violation.detected_at.desc()).offset((page - 1) * limit).limit(limit).all()
        return items, total

    def update_status(self, violation_id: str, status: str, reviewed_by: str | None = None) -> Violation | None:
        v = self.db.query(Violation).filter(Violation.id == violation_id).first()
        if v:
            v.status = status
            if reviewed_by:
                v.reviewed_by = reviewed_by
            self.db.commit()
            self.db.refresh(v)
        return v

    def count_by_type(self) -> list[dict]:
        rows = (
            self.db.query(Violation.violation_type, func.count(Violation.id), func.avg(Violation.confidence))
            .group_by(Violation.violation_type)
            .all()
        )
        return [{"type": r[0], "count": r[1], "avg_confidence": round(r[2], 3)} for r in rows]

    def count_by_date(self, days: int = 30) -> list[dict]:
        rows = (
            self.db.query(func.date(Violation.detected_at), func.count(Violation.id))
            .group_by(func.date(Violation.detected_at))
            .order_by(func.date(Violation.detected_at).desc())
            .limit(days)
            .all()
        )
        return [{"date": str(r[0]), "count": r[1]} for r in rows]

    def total_count(self) -> int:
        return self.db.query(func.count(Violation.id)).scalar() or 0
