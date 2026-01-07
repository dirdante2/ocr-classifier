# database/schemas.py
# Pydantic Datenmodelle für API-Kommunikation

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class CornerPoint(BaseModel):
    """Einzelner Eckpunkt."""
    x: int
    y: int
    label: str


class CornersResponse(BaseModel):
    """Eckpunkte-Response."""
    points: List[CornerPoint]
    detection_method: str
    confidence: float


class ScoresResponse(BaseModel):
    """Klassifizierungs-Scores."""
    AR: float
    TP: float
    DOC: float
    PHOTO: float


class ClassificationResponse(BaseModel):
    """Haupt-Klassifizierungs-Response."""
    predicted: str
    confidence: float
    scores: ScoresResponse
    corners: CornersResponse


class FeedbackRequest(BaseModel):
    """User-Feedback Request."""
    classification_id: str
    corrected_class: Optional[str] = None
    user_confidence: str = Field(..., pattern="^(low|medium|high)$")
    correction_reason: Optional[str] = None
    corrected_corners: Optional[List[Dict[str, int]]] = None


class ClassificationData(BaseModel):
    """Daten für CI4-Speicherung."""
    classification_id: str
    timestamp: datetime
    image_hash: str
    prediction: Dict[str, Any]
    features: Dict[str, Any]
    model_version: str
    weights_version: str


class FeedbackData(BaseModel):
    """Feedback-Daten für CI4."""
    classification_id: str
    timestamp: datetime
    user_correction: Dict[str, Any]
    corrected_corners: Optional[List[Dict]] = None
