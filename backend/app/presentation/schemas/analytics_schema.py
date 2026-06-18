from pydantic import BaseModel


class SummaryResponse(BaseModel):
    total_violations: int
    today_violations: int
    avg_confidence: float
    pending_review: int


class TypeCount(BaseModel):
    type: str
    count: int
    avg_confidence: float


class DateCount(BaseModel):
    date: str
    count: int


class SeverityCount(BaseModel):
    severity: str
    count: int
