from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any


class TriageRequest(BaseModel):
    """
    Request model for patient triage endpoint.

    Example:
    {
        "patient_id": "patient_123",
        "symptoms": "I have a headache and fever for 2 days",
        "fhir_token": "eyJhbGc.....",
        "conversation_id": "abc-123"
    }
    """
    patient_id: str = Field(
        ...,
        description="Unique patient identifier",
        min_length=1,
        max_length=100
    )

    symptoms: str = Field(
        ...,
        description="Patient's description of their symptoms",
        min_length=3,
        max_length=2000
    )

    fhir_token: Optional[str] = Field(
        None,
        description="FHIR authentication token (provided by platform)"
    )

    @validator("symptoms")
    def symptoms_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Symptoms cannot be empty")
        return v.strip()
    
    @validator("patient_id")
    def patient_id_valid(cls, v):
        if not v or not v.strip():
            raise ValueError("Patient Id cannot be missing")
        return v.strip()
    


class FeedbackRequest(BaseModel):
    """
    Request model for rating a recommendation (for episodic memory).
    """

    patient_id: str = Field(..., description="Patient identifier")
    conversation_id: str = Field(..., description="Conversation to rate")
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    feedback: Optional[str] = Field(None, description="Optional text feedback")



class HistoryRequest(BaseModel):
    """
    Request model for fetching patient History
    """

    patient_id: str = Field(..., description="Patient Identifier")
    limit: int = Field(10, ge=1, le=50, description="Number of past session to return")