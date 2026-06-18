from sqlalchemy import func
from sqlalchemy.orm import Session

from app.data_access.models import Violation


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_summary(self) -> dict:
        total = self.db.query(func.count(Violation.id)).scalar() or 0
        today = self.db.query(func.count(Violation.id)).filter(
            func.date(Violation.detected_at) == func.date(func.now())
        ).scalar() or 0
        avg_conf = self.db.query(func.avg(Violation.confidence)).scalar() or 0
        pending = self.db.query(func.count(Violation.id)).filter(Violation.status == "pending").scalar() or 0

        return {
            "total_violations": total,
            "today_violations": today,
            "avg_confidence": round(float(avg_conf), 3),
            "pending_review": pending,
        }

    def get_by_type(self) -> list[dict]:
        rows = (
            self.db.query(Violation.violation_type, func.count(Violation.id), func.avg(Violation.confidence))
            .group_by(Violation.violation_type)
            .all()
        )
        return [{"type": r[0], "count": r[1], "avg_confidence": round(float(r[2]), 3)} for r in rows]

    def get_trends(self, days: int = 30) -> list[dict]:
        rows = (
            self.db.query(func.date(Violation.detected_at), func.count(Violation.id))
            .group_by(func.date(Violation.detected_at))
            .order_by(func.date(Violation.detected_at).desc())
            .limit(days)
            .all()
        )
        return [{"date": str(r[0]), "count": r[1]} for r in rows]

    def get_by_severity(self) -> list[dict]:
        rows = (
            self.db.query(Violation.severity, func.count(Violation.id))
            .group_by(Violation.severity)
            .all()
        )
        return [{"severity": r[0], "count": r[1]} for r in rows]
