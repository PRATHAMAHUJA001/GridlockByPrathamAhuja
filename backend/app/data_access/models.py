import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.data_access.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), default="operator")
    created_at = Column(DateTime, default=datetime.utcnow)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(String, primary_key=True, default=gen_uuid)
    plate_number = Column(String(20), index=True)
    plate_confidence = Column(Float)
    vehicle_category = Column(String(30), nullable=False)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    metadata_ = Column("metadata", JSON)

    violations = relationship("Violation", back_populates="vehicle")


class Image(Base):
    __tablename__ = "images"

    id = Column(String, primary_key=True, default=gen_uuid)
    file_path = Column(String(500), nullable=False)
    image_type = Column(String(20), nullable=False)
    width = Column(Integer)
    height = Column(Integer)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(50))


class Violation(Base):
    __tablename__ = "violations"

    id = Column(String, primary_key=True, default=gen_uuid)
    violation_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(10), nullable=False)
    confidence = Column(Float, nullable=False)
    bbox_x = Column(Integer)
    bbox_y = Column(Integer)
    bbox_w = Column(Integer)
    bbox_h = Column(Integer)
    vehicle_id = Column(String, ForeignKey("vehicles.id"))
    original_image_id = Column(String, ForeignKey("images.id"), nullable=False)
    evidence_image_id = Column(String, ForeignKey("images.id"))
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    location = Column(String(200))
    status = Column(String(20), default="pending")
    reviewed_by = Column(String, ForeignKey("users.id"))
    metadata_ = Column("metadata", JSON)

    vehicle = relationship("Vehicle", back_populates="violations")
    original_image = relationship("Image", foreign_keys=[original_image_id])
    evidence_image = relationship("Image", foreign_keys=[evidence_image_id])


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id = Column(String, primary_key=True, default=gen_uuid)
    snapshot_date = Column(String(10), nullable=False)
    violation_type = Column(String(50))
    total_count = Column(Integer, default=0)
    avg_confidence = Column(Float)
    computed_at = Column(DateTime, default=datetime.utcnow)
