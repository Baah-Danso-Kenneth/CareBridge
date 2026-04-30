from backend.app.memory import episodic
from app.tools import patient_history
from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict):
    """
    State that flows through the LangGraph.
    Every node reads from and writes to this state.
    This is the ONLY way data moves between agents.
    """

    patient_id: str
    symptoms: str
    conversation_id: str
    plan: Dict[str, Any]
    plan_steps: List[Dict]

    patient_history: Dict[str, Any]
    symptom_analyis: Dict[str, Any]
    urgency_result: Dict[str, Any]

    raw_recommendation: str
    final_recommendation: str

    critic_score: float
    critic_verdict: str
    critic_feedback: str
    attempt_number: int


    guardrail_passed: bool
    guardrail_violations: List[Dict]
    disclaimer_added: bool

    episodic_context: Dict[str, Any]

    errors: List[str]
    execution_trace: List[str]
    




    def create_initial_state(
        patient_id: str,
        symptoms: str,
        conversation_id: Optional[str] = None
        ) -> AgentState: 
        """Create a fresh initial state for a patient interaction"""
        import uuid

        return {
            "patient_id": patient_id,
            "symptoms": symptoms,
            "conversation_id": conversation_id or str(uuid.uuid4()),

            "plan": {},
            "plan_steps": [],
            
            "patient_history": {},
            "symptom_analyis": {},
            "urgency_result": {},

            "raw_recommendation": "",
            "final_recommendation": "",
            "critic_score": 0.0,
            "critic_verdict": "",
            "critic_feedback": "",
            "attempt_number": 1,

            "guardrail_passed": False,
            "guardrail_violations": [],
            "disclaimer_added": False,

            "episodic_context": {},

            "errors": [],
            "execution_trace": []
        }


    def add_to_trace(state: AgentState, message: str):
        """Add a message to the execution trace for debugging"""
        trace = state.get("execution", [])
        trace.append(message)
        state["execution_trace"] = trace
        return state
    
    def add_error(state: AgentState, error: str) -> AgentState:
        """Add errors to the state"""
        errors = state.get("errors", [])
        errors.append(error)
        state["errors"] = errors
        return state

    def has_errors(state: AgentState) -> bool:
        """Check if state has any errors"""
        return len(state.get("errors",[])) > 0

    
    def increment_attempt(state: AgentState) -> AgentState:
        """Increment the attempt counter"""
        state["attempt_number"] = state.get("attempt_number", 1) + 1
        return state


    def is_max_attempts_reacehd(state: AgentState, max_attempts: int = 3) -> bool:
        """Check if max attempts reached"""
        return state.get("attempt_number", 1) > max_attempts