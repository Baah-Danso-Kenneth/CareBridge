from app.utils import logging
import logging
from typing import Dict, Any


from app.graph.state import AgentState, add_to_trace, add_error
from app.agents.planner import PlannerAgent
from app.agents.executor import ExecutorAgent
from app.agents.critic import CriticAgent
from app.agents.base import A2ATask


logger = logging.getLogger(__name__)



planner_agent = None
executor_agent = None
critic_agent = None



def set_agent(planner: PlannerAgent, executor: ExecutorAgent, critic: CriticAgent):
    """ Inject agent instances in nodes """
    global planner_agent, executor_agent, critic_agent

    planner_agent = planner
    executor_agent = executor
    critic_agent = critic

    logger.info("Agents injected into graph nodes")



def planner_node(state: AgentState) -> Dict[str, Any]:
    """Create execution plan from patient symptoms"""
    logger.info(f"PlannerNode: processing patient {state.get("patient_id")}")
    symptoms = state.get("symptoms")
    patient_id = state.get("patient_id", "unknown")

    if not symptoms:
        add_error(state, "No symptoms provided to planner")
        return {"errors": state.get("errors",[])}

    task = A2ATask(
        objective=f"Analyze symptoms for patient {patient_id}",
        context={
            "symptoms": symptoms,
            "patient_id": patient_id,
            "attempt": state.get("attempt_number", 1)
        }
    )

    result_task = planner_agent.process_task(task)

    if result_task.status == "failed":
        add_error(state, f"Planner failed: {result_task.errors}")
        return {"errors": state.get("errors", [])}

    plan = result_task.result.get("plan",{})
    steps = plan.get("steps", [])

    add_to_trace(state, f"Planner created plan with {len(steps)} steps")
    logger.info(f"Created plan with {len(steps)} steps")


    return {
        "plan": plan,
        "plan_steps": steps
    }





def executor_node(state: AgentState) -> Dict[str, Any]:
    """Execute plan for calling MCP Tools """
    logger.info(f"ExecutorNode: executiing {len(state.get("plan_steps",[]))} steps")

    symptoms = state.get("symptoms", "")
    patient_id = state.get("patient_id", "unknown")   
    plan = state.get("plan", {})
    attempt = state.get("attempt_number", 1)

    revision_feedback = ""

    if attempt > 1:
        revision_feedback = state.get("critic_feedback", "")
        logger.info(f" Revision attempt {attempt}, feedback : {revision_feedback[:100]}")

    task = A2ATask(
        objective=f"ExecutorAgent healthcare plan for patient {patient_id}",
        context={
            "plan": plan,
            "symptoms": symptoms,
            "patient_id": patient_id,
            "attempt": attempt,
            "revision_feedback": revision_feedback
        }
    )


    result_task = executor_node.process_task(task)

    if result_task.status == "failed":
        add_error(state, f"Executor failed: {result_task.errors}")
        return {"errors": state.get("errors", [])}

    recommendation = result_task.result.get("recommendation", "")
    urgency_level = result_task.result.get("urgency_level", "UNKNOWN")
    patient_history = result_task.result.get("patient_history", {})
    symptom_analysis = result_task.result.get("symptom_analysis", {})
    guardrail_passed = result_task.result.get("guardrail_passed", False)

    add_to_trace(state, f"Executor produced recommendation (urgency: {urgency_level})")
    logger.info(f"Recommendation produced, urgency: {urgency_level}")


    return {
        "raw_recommendation": recommendation,
        "patient_history": patient_history,
        "symptom_analysis": symptom_analysis,
        "urgency_result": {"urgency_level": urgency_level},
        "guardrail_passed": guardrail_passed
    }

def critic_node(state: AgentState) -> Dict[str, Any]:
    """Evaluate recommendation and issue verdict."""
    logger.info(f"CriticNode: evaluating the recommendation")

    recommendation = state.get("raw_recommendation")
    symptoms = state.get("symptoms", "")
    attempt = state.get("attempt_number", 1)

    if not recommendation:
        add_error(state, "No recommendation to evaluate")
        return {"errors": state.get("errors", [])}


    task = A2ATask(
        objective="Evaluate healthcare recommendation",
        context={
            "recommendation": recommendation,
            "symptoms": symptoms,
            "attempt": attempt
        }
    )

    result_task = critic_agent.process_task(task)

    if result_task.status == "failed":
        add_error(state, f"Critic failed:{result_task.error}")
        return {"errors": state.get("errors",[])}

    score = result_task.result.get("score", 0)
    verdict = result_task.result.get("verdict", "REVISE")
    feedback = result_task.result.get("feedback", "")

    add_to_trace(state, f"Critic scored {score}/100, verdict: {verdict}")
    logger.info(f"Score:{score}/100, Verdict: {verdict}")

    return {
        "critic_score": score,
        "critic_verdict": verdict,
        "critic_feedback": feedback,
        "attempt_number": attempt + 1
    }

def guardrail_node(state: AgentState) -> Dict[str, Any]:
    """Apply final safety checks and disclaimer"""
    logger.info(f"GuardrailNode: running safety Scan")

    recommendation = state.get("raw_recommendation")

    disclaimer_keywords = ["not medical advice", "consult a", "health proffessional"]
    has_disclaimer = any(kw in recommendation.lower() for kw in disclaimer_keywords)

    final_recommendation = recommendation
    disclaimer_added = False

    if not has_disclaimer:
        disclaimer = "\n\n**Disclaimer:** This is not medical advice Consult a healthcare proffessional"
        final_recommendation = recommendation + disclaimer
        logger.info("Added medical disclaimer ")

    logger.info("Guardrail check complete")

    return {
        "final_recommendation": final_recommendation,
        "disclaimer_added": disclaimer_added
    }



def output_node(state: AgentState)-> Dict[str, Any]:
    """Prepare final output"""
    logger.info("OutputNode: Preparing final response")
    
    final_recommendation = state.get("final_recommendation", "")
    score = state.get("critic_score", 0)
    verdict = state.get("critic_verdict", "UNKNOWN")
    attempts = state.get("attempt_number", 1) - 1

    add_to_trace(state, f"Output prepared after {attempts} attempts , {score} Score")
    logger.info(f"Final output ready (attempts: {attempts}, score: {score})")

    return {}