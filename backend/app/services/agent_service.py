import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path

from app.config import config
from app.utils import create_default_knowledge_base
from app.graph.graph import run_graph
from app.graph.nodes import set_agent
from app.agents.planner import PlannerAgent
from app.agents.executor import ExecutorAgent
from app.agents.critic import CriticAgent
from app.memory.episodic import EpisodicMemory
from app.memory.semantic import SemanticMemory
from app.memory.procedural import ProceduralMemory
from app.graph.state import create_initial_state


logger = logging.getLogger(__name__)


class AgentService:
    """
    Main service that orchestrate the entire agent system:
    Responsibilities:
    1. Initialize all components (memory, agents, graphs)
    2. Process patient triage requests
    3. Store session history in episodic memory
    """

    def __init__(self):
        self.procedural_memory = ProceduralMemory()
        knowledge_path = Path(__file__).parent.parent.parent / "data" / "medical_knowledge.json"

        if not knowledge_path.exists():
            create_default_knowledge_base(str(knowledge_path))
            logger.info(f"Created default knowledge base at {knowledge_path} ")
        
        self.semantic_memory = SemanticMemory(knowledge_path)
        logger.info("Semantic memory initialized (FAISS + Cohere)")

        self.planner = PlannerAgent()
        self.executor = ExecutorAgent()
        self.critic = CriticAgent()
        logger.info("A2A Agents initialized (Planner, Executor, Critic)")

        set_agent(self.planner, self.executor, self.critic)
        logger.info("Agents injected into LangGraph nodes")

    
    def triage(self, patient_id: str, symptoms: str,
                fhir_token: Optional[str]=None,
                fhir_url: Optional[str] = None,
                conversational_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a patient triage request.

        Args.
            patient_id: unique patient identifier
            symptoms: Patient's description of symptoms
            fhir_token: Optional FHIR authentication token
            conversation_id: Optional existing conversation ID

        Returns:
            Dict with recommendation, urgency level, quality score etc..
        """

        start_time = time.time()

        episodic_memory = EpisodicMemory(patient_id)
        episodic_context = episodic_memory.get_recent_sessions(limit=3)

        if episodic_context:
            logger.info(f"Loaded {len(episodic_context)} past sessions from episodic memory")

        initial_state = create_initial_state(
            patient_id=patient_id,
            symptoms=symptoms,
            conversation_id=conversational_id
        )
        
        initial_state["fhir_url"]=fhir_url
        initial_state["fhir_token"] = fhir_token
        
        initial_state["episodic_context"] = {
            "recent_sessions": episodic_context,
            "preferences": episodic_memory.get_preferences()
        }

        try:
            final_state = run_graph(initial_state)

        except Exception as e:
            logger.error(f"Graph execution failed {e}")
            return {
                "error": str(e),
                "success": False,
                "patient_id": patient_id
            }
        
        final_recommendation = final_state.get("final_recommendation", "")
        raw_recommendation = final_state.get("raw_recommendation", "")
        score = final_state.get("critic_score", 0)
        verdict = final_state.get("critic_verdict", "UNKNOWN")
        attempts = final_state.get("attempt_number",1) - 1
        urgency_result = final_state.get("urgency_result", {})
        symptom_analysis = final_state.get("symptom_analysis", {})
        logger.info(f"DEBUG: symptom_analysis from final_state: {symptom_analysis}")
        logger.info(f"DEBUG: conditions: {symptom_analysis.get('conditions', [])}")
        disclaimer_added = final_state.get("disclaimer_added", False)
        errors = final_state.get("errors", [])


        processing_time = int((time.time() - start_time) * 1000)

        episodic_memory.add_session(
            symptoms = symptoms,
            urgency_level = urgency_result,
            recommendation = final_recommendation or raw_recommendation,
            score = score
            )


        logger.info("Stored session in episodic memory")

        response = {
            "success": not errors,
            "conversation_id": final_state.get("conversation_id"),
            "patient_id": patient_id,
            "recommendation": final_recommendation or raw_recommendation,
            "urgency_level": urgency_result.get("urgency_level", "UNKNOWN"),
            "possible_conditions": symptom_analysis.get("conditions",[]),
            "score": score,
            "verdict": verdict,
            "attempts_used": attempts,
            "disclaimer_added": disclaimer_added,
            "processing_time_ms": processing_time,
            "errors": errors if errors else None

        }

        return response
    


    def get_patient_history(self, patient_id: str, limit: int=10) -> Dict[str, Any]:
        """
        Get Patient's triage history from episodic memory
        """
        episodic_memory = EpisodicMemory(patient_id)
        sessions = episodic_memory.get_recent_sessions(limit=limit)

        return {
            "patient_id": patient_id,
            "total_sessions": episodic_memory.get_session_count(),
            "sessions": sessions
        }
    


    def rate_recommendation(self, patient_id: str, conversation_id: str, rating: int, feedback: Optional[str]=None) -> Dict[str, Any]:
        """
        Rate a recommendation (for improving episodic memory)
        """
        return {
            "success": True,
            "message": f"Rating {rating}/5 recorded",
            "patient_id": patient_id
        }
    

    def get_system_status(self) -> Dict[str, Any]:
        """Get system health status"""

        return {
            "status": "healthy",
            "components": {
                "semantic_memory": self.semantic_memory.index is not None,
                "agents": {
                    "planner": True,
                    "executor": True,
                    "critic": True
                }
            }
        }
        












