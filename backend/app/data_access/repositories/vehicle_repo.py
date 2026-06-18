from sqlalchemy.orm import Session, joinedload

from app.data_access.models import Vehicle


class VehicleRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, vehicle: Vehicle) -> Vehicle:
        self.db.add(vehicle)
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def get_by_id(self, vehicle_id: str) -> Vehicle | None:
        return self.db.query(Vehicle).options(joinedload(Vehicle.violations)).filter(Vehicle.id == vehicle_id).first()

    def search_by_plate(self, plate: str) -> list[Vehicle]:
        return self.db.query(Vehicle).filter(Vehicle.plate_number.ilike(f"%{plate}%")).all()

    def find_by_plate(self, plate: str) -> Vehicle | None:
        return self.db.query(Vehicle).filter(Vehicle.plate_number == plate).first()
