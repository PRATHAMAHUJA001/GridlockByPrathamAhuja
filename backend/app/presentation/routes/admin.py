import shutil

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.data_access.database import get_db
from app.data_access.models import AnalyticsSnapshot, Image, Vehicle, Violation, User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.delete("/clean-db")
def clean_database(db: Session = Depends(get_db)):
    """Wipe all data from the database and clear uploaded/evidence files."""
    counts = {
        "violations": db.query(Violation).count(),
        "vehicles": db.query(Vehicle).count(),
        "images": db.query(Image).count(),
        "snapshots": db.query(AnalyticsSnapshot).count(),
    }

    db.query(Violation).delete()
    db.query(Vehicle).delete()
    db.query(Image).delete()
    db.query(AnalyticsSnapshot).delete()
    db.commit()

    # Clear upload and evidence directories
    for d in [settings.UPLOAD_DIR, settings.EVIDENCE_DIR]:
        if d.exists():
            shutil.rmtree(d)
            d.mkdir(exist_ok=True)

    return {
        "message": "Database cleaned successfully",
        "deleted": counts,
    }


@router.get("/db-stats")
def db_stats(db: Session = Depends(get_db)):
    """Get current database table counts."""
    return {
        "violations": db.query(Violation).count(),
        "vehicles": db.query(Vehicle).count(),
        "images": db.query(Image).count(),
        "users": db.query(User).count(),
        "snapshots": db.query(AnalyticsSnapshot).count(),
    }
