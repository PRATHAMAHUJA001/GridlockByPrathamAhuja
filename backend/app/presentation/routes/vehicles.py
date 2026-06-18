from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.data_access.database import get_db
from app.data_access.repositories.vehicle_repo import VehicleRepository

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("/search")
def search_vehicles(plate: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    repo = VehicleRepository(db)
    vehicles = repo.search_by_plate(plate)
    return [
        {
            "id": v.id,
            "plate_number": v.plate_number,
            "vehicle_category": v.vehicle_category,
            "plate_confidence": v.plate_confidence,
            "first_seen_at": v.first_seen_at,
        }
        for v in vehicles
    ]


@router.get("/{vehicle_id}")
def get_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    repo = VehicleRepository(db)
    v = repo.get_by_id(vehicle_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return {
        "id": v.id,
        "plate_number": v.plate_number,
        "vehicle_category": v.vehicle_category,
        "plate_confidence": v.plate_confidence,
        "first_seen_at": v.first_seen_at,
        "violations": [
            {
                "id": viol.id,
                "violation_type": viol.violation_type,
                "severity": viol.severity,
                "confidence": viol.confidence,
                "detected_at": viol.detected_at,
            }
            for viol in v.violations
        ],
    }
