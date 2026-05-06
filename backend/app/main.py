import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

from app.services.agent_service import AgentService
from app.models.requests import (
    TriageRequest,
     FeedbackRequest
)
from app.models.response import (
    TriageResponse, ErrorResponse,
    FeedbackResponse, HistoryResponse
)
from app.utils.logging import setup_logging

setup_logging()

logger = logging.getLogger(__name__)


app = FastAPI(
    title="CareBridge - Healthcare Triage Agent",
    description="Autonomous AI agent for patient symptom triage and urgency classification",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

try:
    agent_service = AgentService()
    logger.info("Agent service initialized successfully")

except Exception as e:
    logger.error(f"Failed to initialize agent service {e}")
    raise



@app.post("/")
async def handle_a2a_message(request: Dict[str, Any]):
    """
    A2A endpoint for Prompt Opinion Platform.
    Receives messages in JSON-RPC format with FHIR context in metadata
    """

    logger.info(f"A2A message receied: {request.get("method")}")

    try:
        params = request.get("params", {})
        message = params.get("message", {})
        metadata = message.get("metadata", {})
        fhir_context = metadata.get("https://app.promptopinion.ai/schemas/a2a/v1/fhir-context", {})

        fhir_url = fhir_context.get("fhirUrl")
        fhir_token = fhir_context.get("fhirToken")
        patient_id = fhir_context.get("patientId")

        parts = message.get("pars", [])

        symptoms = ""

        for part in parts:
            if isinstance(part, dict) and "text" in part:
                symptoms = part["text"]
                break
            elif isinstance(part, str):
                symptoms = part
                break

        if not symptoms:
            symptoms = message.get("text", "")


        result = agent_service.triage(
            patient_id = patient_id or "UNKNOWN",
            symptoms=symptoms,
            fhir_token=fhir_token,
            fhir_url=fhir_url,
            conversational_id=None
        )

        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),

            "result": {
                "message": {
                    "role": "assistant",
                    "parts": [{"text": result.get("recommendation", "Unable to pass result")}]
                }
            }
        }
    
    except Exception as e:
        logger.error(f"A2A endpoint failed: {e}")

        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }




@app.get("/default", tags=["Health"])
async def root():
    """Root endpoint - API information """
    return {
        "service": "CareBridge",
        "version": "2.0.0",
        "description": "HealthCare Triage Agent",
        "status": "running",
        "endpoints": [
            "POST /triage - Analyze patient symptoms",
            "GET /history/{patient_id} - Get patient triage history",
            "POST /feedback - Rate a patient triage history",
            "GET /status - System health status",
            "GET /docs - API documentation"
        ]
    }


@app.get("/status", tags=["Health"])
async def get_status():
    """Get system health status"""
    try:
        status = agent_service.get_system_status()
        return {"status": "healthy", **status}
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}




    
@app.post(
    "/triage",
    response_model=TriageResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    },
    tags=["Triage"]
)
async def triage(request: TriageRequest):
    """
    Analyze patient symptoms and provide urgency classification.
    
    **Input:**
    - patient_id: Unique patient identifier
    - symptoms: Description of symptoms
    - fhir_token: Optional FHIR authentication token
    - conversation_id: Optional existing conversation ID

    **Output**
    - recommendation: Human-readable advice
    - urgency_level: ROUTINE, SOON, URGENT, or EMERGENCY
    - quality_score: 0-100 quality score from critic
    - possible_conditions: List of potential conditions with confidence
    """

    logger.info(f"POST /triage - Patient: {request.patient_id}")

    try:
        result = agent_service.triage(
            patient_id=request.patient_id,
            symptoms=request.symptoms,
            fhir_token=request.fhir_token,
            conversational_id=request.conversation_id
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("errors", ["Unknown error"])[0]
            )

        return TriageResponse(
            conversation_id=result["conversation_id"],
            patient_id = result["patient_id"],
            recommendation=result["recommendation"],
            urgency_level = result["urgency_level"],
            possible_conditions= result.get("possible_conditions", []),
            quality_score = result["score"],
            attempts_used = result["attempts_used"],
            disclaimer_added = result["disclaimer_added"],
            processing_time_ms=result["processing_time_ms"]
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Triage endpoint failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

    
@app.get(
    "/history/{patient_id}",
    response_model=HistoryResponse,
    tags=["History"]
)
async def get_history(patient_id: str, limit: int = 10):
    """
    Get patient's triage history from episodic memory.

    **Input:**
    - patient_id: Patient ID
    - limit: Number of past sessions to return (max 10)

    **Output:**
    - total_sessions: Total number of sessions
    - sessions: List of past triage sessions
    """

    logger.info(f"GET /history/{patient_id}")

    try:
        limit = min(limit, 50)
        result = agent_service.get_patient_history(patient_id, limit)

        return HistoryResponse(
            patient_id=result["patient_id"],
            total_sessions= result["total_sessions"],
            sessions=result["sessions"]
        )

    except Exception as e:
        logger.error(f"History endpoint failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve history: {str(e)}"

        )



@app.post(
    "/feedback",
    response_model=FeedbackResponse,
    tags=["Feedback"]
)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit rating for a recommendation.
    used to improve episodic memory and taste learning.

    **Input:**
    - patient_id: Patient Identifier
    - conversation_id: Conversation being rated
    - rating: 1 - 5 rating
    - feedback: Optional text feedback
    """

    logger.info(f"POST /feedback - Patient: {request.patient_id}")

    try:
        result = agent_service.rate_recommendation(
            patient_id=request.patient_id,
            conversation_id=request.conversation_id,
            rating= request.rating,
            feedback=request.feedback
        )

        return FeedbackResponse(
            success=result["success"],
            message=result["message"]
        )

    except Exception as e:
        logger.error(f"Feedback endpoint failed {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit feedback: {e}"
        )