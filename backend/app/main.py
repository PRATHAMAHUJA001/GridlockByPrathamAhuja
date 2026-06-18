from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.data_access.database import Base, engine
from app.presentation.routes import admin, analytics, auth, detection, evaluation, health, vehicles, violations

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TrafficSarathi", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(detection.router, prefix="/api/v1")
app.include_router(violations.router, prefix="/api/v1")
app.include_router(vehicles.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(evaluation.router, prefix="/api/v1")

app.mount("/api/v1/files/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")
app.mount("/api/v1/files/evidence", StaticFiles(directory=str(settings.EVIDENCE_DIR)), name="evidence")
