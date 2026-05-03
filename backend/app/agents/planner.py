from app.utils import logging
import json
import logging
from typing import Dict, Any


from app.agents.base import A2AAgent, A2ATask, A2AAgentCard, A2ATaskStatus
from app.prompts.medical_prompts import PLANNER_SYSTEM_PROMPT, PLANNER_HUMAN_PROMPT

logger = logging.getLogger(__name__)


class PlannerAgent(A2AAgent):
    """
    Planner Agent - Creates execution plan from patient symptoms

    Takes patient symptoms and returns a structured plan with steps
    1. Fetch patient history
    2. Analyze symptoms
    3. Classify urgency
    4. Generate recommendation

    """

    def _register_card(self) -> A2AAgentCard:
        return A2AAgentCard(
            name="planner-agent",
            version="1.0.0",
            description="Creates execution plans from symptoms",
            input_modes=["text"],
            output_modes=["structured_plan"],
            endpoint="in-process://planner-agent",
            skills=[{
                "name": "create_plan",
                "description": "Create execution",
                "input": {"symptoms": "string"},
                "output": {"plan": "dict", "steps": "list"}
            }]
        )


    def process_task(self, task: A2ATask) -> A2ATask:
        """ Process patient symptoms and create execution"""
        task.update_status(A2ATaskStatus.WORKING)
        logger.info(f"PlannerAgent:Creating plan for patient")

        try:
            symptoms = task.context.get("symptoms", "")
            patient_id = task.context.get("patient_id", "unknown")

            if not symptoms:
                task.errors.append("No symptoms provided")
                task.update_status(A2ATaskStatus.FAILED)
                return task

            # Create plan using LLM
            plan = self._create_plan(symptoms, patient_id)

            task.result = {
                "plan": plan,
                "patient_id": patient_id,
                "symptoms": symptoms,
                "steps_count": len(plan.get("steps", []))
            }

            task.update_status(A2ATaskStatus.COMPLETED)
            logger.info(f"PlannerAgent: Created plan with {len(plan.get("steps", []))} steps")

        except Exception as e:
            logger.error(f"PlannerAgent failed: {e}")
            task.errors.append(str(e))
            task.update_status(A2ATaskStatus.FAILED)


        self._record_task(task)
        return task



    def _create_plan(self, symptoms: str, patient_id: str) -> Dict[str, Any]:
        """Create execution plan using LLM"""

        human_prompt = PLANNER_HUMAN_PROMPT.format(
            symptoms=symptoms,
            patient_id = patient_id
        )
        
        response = self._invoke_llm(PLANNER_SYSTEM_PROMPT, human_prompt)

        # Clean and parse JSON

        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        plan = json.loads(clean)

        if "steps" not in plan:
            plan["steps"] = self._get_default_steps()
        
        return plan



    def _get_default_steps(self) -> list:
        """ Fallback plan if LLM fails """
        return [
            {
                "step_id": 1, 
                "tool": "PatientHistoryTool",
                "description": "Fetch patient medical history"
            },

            {
                "step_id": 2, 
                "tool": "SymptomAnalyzerTool",
                "description": "Analyze symptoms"
            },

            {
                "step_id": 3,
                "tool": "UrgencyClassifierTool",
                "description": "Classify urgency level"
            },

            {
                "step_id": 4,
                "tool": "GuardrailTool",
                "description": "Check Safety"
            }
        ]