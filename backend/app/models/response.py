from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ConditionResult(BaseModel):
    """Possible condition from symptom analysis"""
    name: str = Field(..., description="Condition analysis")
    confidence: float = Field(..., ge=0, le=1, description="Confidence Score 0-1" )
    reasoning: str = Field(..., description="Wy this condition is possible")
    self_care: List[str] = Field(default_factory=list, description="Self-care suggestion")


class UrgencyResult(BaseModel):
    """Urgency classification result"""
    level: str = Field(..., description="ROUTINE, SOON, URGENT, or EMERGENCY")
    confidene: float = Field(..., ge=0, le=1, description="Confidence score 0-1")
    reasoning: str = Field(..., description="Wy this condition is possible")
    recommendation_action: str = Field(..., description="What patient should do")


class TriageResponse(BaseModel):
    """Response model for patient triage endpoint"""

    conversation_id: str = Field(..., description="Unique conversation ID")
    patient_id: str = Field(..., description="Patient identifier")
    recommendation: str = Field(..., description="Humn-readable recommendation for patient")

    urgency_level: str = Field(..., description="ROUTINE, SOON, URGENT, or EMERGENCY")
    possible_conditions: List[ConditionResult] = Field(default_factory=list)

    quality_score: float = Field(..., ge=0, le=100, description="Critic's quality score(0-1000)")
    attempts_used: int = Field(..., ge=1, le=3, description="Number of self-correction attempts")

    disclaimer_added: bool = Field(..., description="Whether medical dislaimer was added or Not")

    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")
    timestamp: datetime = Field(..., default_factory=datetime.now)


    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "abc-123-def",
                "patient_id": "patient_123",
                "recommendation": "Based on your symptoms, you may have a viral infection. Rest, hydrate, and monitor your temperature. See a doctor if fever exceeds 103°F or symptoms worsen after 3 days.",
                "urgency_level": "SOON",
                "possible_conditions": [
                    {
                        "name": "Viral Upper Respiratory Inspection",
                        "confidence": 0.85,
                        "reasoning": "Headache and fever are classic viral symptoms",
                        "self_care": ["Rest", "Hydration"]
                    }
                ],
                "quality_score": 85.0,
                "attempts_used": 1,
                "disclaimer_added": True,
                "processing_time_ms": 2345,
                "timestamp": "2026-04-30T10:30:00"

            }
        }


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type (validation, processing, etc ..)")
    conversation_id: Optional[str] = Field(None, description="Conversation ID if available")
    timestamp: datetime = Field(default_factory=datetime.now)


class FeedbackResponse(BaseModel):
    """Response model for rating feedback."""

    success: bool = Field(..., description="Whether rating was recorded")
    message: str = Field(..., description="Status message")



class HistoryResponse(BaseModel):
    """Response model for patient history ."""

    patient_id: str = Field(..., description="Patient identifier")
    total_sessions: int = Field(..., description="Total number of session")
    sessions: List[Dict[str, Any]] = Field(..., description="Past session data")

