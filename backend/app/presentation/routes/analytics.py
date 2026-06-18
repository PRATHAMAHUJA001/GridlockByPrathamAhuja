from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.data_access.database import get_db
from app.service.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    return AnalyticsService(db).get_summary()


@router.get("/by-type")
def get_by_type(db: Session = Depends(get_db)):
    return AnalyticsService(db).get_by_type()


@router.get("/trends")
def get_trends(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    return AnalyticsService(db).get_trends(days)


@router.get("/by-severity")
def get_by_severity(db: Session = Depends(get_db)):
    return AnalyticsService(db).get_by_severity()
