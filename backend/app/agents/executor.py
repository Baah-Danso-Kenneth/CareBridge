import json
import json
import logging
from typing import Dict, List, Any

from app.agents.base import A2AAgent, A2AAgentCard, A2ATask, A2ATaskStatus
from app.tools.patient_history import PatientHistoryTool
from app.tools.symptom_analyzer import SymptomAnalyzerTool
from app.tools.urgency_classifier import UrgencyClassifierTool
from app.tools.guardrail import GuardrailTool
from app.prompts.medical_prompts import EXECUTOR_HUMAN_PROMPT, EXECUTOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)



class ExecutorAgent(A2AAgent):
    """
    Executor Agent - Executes the plan by calling MCP tools.

    Takes a plan from Planner, calls the appropriate tools, 
    and synthesizes results into a patient recommendation
    """

    def __init__(self):
        super().__init__()
        # Initialize MCP tools
        self.patient_history = PatientHistoryTool()
        self.symptom_analyzer = SymptomAnalyzerTool()
        self.urgency_classifier = UrgencyClassifierTool()
        self.guardrail = GuardrailTool()

    
    def _register_card(self) -> A2AAgentCard:
        return A2AAgentCard(
            name="executor-agent",
            version="1.0.0",
            description="Executes health plans using MCP tools",
            capabilities=["mcp_tool_execution", "symptom_analysis", "Urgency_classification"],
            input_modes = ["structured_plan"],
            output_modes = ["recommendation"],
            endpoint="in-process://executor-agent",
            skills=[{
                "name": "execute_plan",
                "description": "Execute plan and produce recommendation",
                "input": {
                    "plan": "dict",
                    "symptoms": "string",
                    "patient_id": "striing",
                },
                "output": {
                    "recommendation": "string",
                    "urgency": "string"
                }
            }],

            extensions= [
                {
                    "uri": "https://app.promptopinion.ai/schemas/a2a/v1/fhir-context",
                    "required": False,
                    "params": {
                        "scopes": [
                            {"name": "patient/Patient.rs", "required" : True},
                            {"name": "patient/Condition.rs", "required" : True},
                            {"name": "patient/MedicationRequest.rs", "required" : True}
                        ]
                    }
                }
            ]
        )


    

    def process_task(self, task: A2ATask) -> A2ATask:
        """Execute the plan and produce recommendation"""

        task.update_status(A2ATaskStatus.WORKING)
        logger.info(f"ExecutorAgent: executing plan")

        try:
            fhir_url = task.context.get("fhir_url")
            fhir_token = task.context.get("fhir_url")

            plan = task.context.get("plan", {})
            symptoms = task.context.get("symptoms", "")
            patient_id = task.context.get("patient_id", "")
            steps = plan.get("steps", [])

            # Storage for tools results

            patient_history = {}
            symptom_analysis = {}
            urgency_result = {}

            for step in steps:
                tool_name = step.get("tool", "")
                logger.info(f"Executing step {step.get("step_id")}: {tool_name}")

                if tool_name == "PatientHistoryTool":
                    result = self.patient_history.execute(
                        patient_id=patient_id,
                        fhir_token=fhir_token,
                        fhir_url=fhir_url
                    )
                    if result.status.value == "success":
                        patient_history = result.content

                elif tool_name == "SymptomAnalyzerTool":
                    result = self.symptom_analyzer.execute(
                        symptoms=symptoms,
                        patient_history=patient_history
                    )

                    if result.status.value == "success":
                        if result.content.get("requires_llm"):
                            logger.info(f"DEBUG: Calling LLM for analysis with prompt: {result.content.get('prompt', {})}")
                            symptom_analysis = self._call_llm_for_analysis(
                                symptoms,
                                patient_history,
                                result.content.get("prompt", {})
                            )
                        else:
                            symptom_analysis = result.content

                elif tool_name == "UrgencyClassifierTool":
                    result = self.urgency_classifier.execute(
                        symptoms=symptoms,
                        patient_history=patient_history,
                        possible_conditions=symptom_analysis.get("conditions",[])
                    )

                    if result.status.value == "success":
                        if result.content.get("requires_llm"):
                            logger.info(f"DEBUG: Calling LLM for urgency with prompt: {result.content.get('prompt', {})}")
                            urgency_result = self._call_llm_for_urgency(
                                symptoms,
                                patient_history,
                                symptom_analysis,
                                result.content.get("prompt",{})
                            )
                        else:
                            urgency_result = result.content
                    
                elif tool_name == "GuardrailTool":
                        pass

            recommendation = self._synthesize_recommendation(
                symptoms=symptoms,
                patient_history=patient_history,
                symptom_analysis=symptom_analysis,
                urgency=urgency_result
            )

            guardrail_result = self.guardrail.execute(recommendation)
            final_recommendation = guardrail_result.content.get("sanitized_content",recommendation)

            task.result = {
                "recommendation": final_recommendation,
                "urgency_level": urgency_result.get("urgency_level", "UNKNOWN"),
                "patient_history": patient_history,
                "symptom_analysis": symptom_analysis,
                "guardrail_passed": guardrail_result.content.get("passed", False)
            }

            task.update_status(A2ATaskStatus.COMPLETED)
            logger.info(f"ExecutorAgent: complete, urgency={urgency_result.get('urgency_level')}")
        
        except Exception as e:
            logger.error(f"ExecutorAgent failed: {e}")
            task.errors.append(str(e))
            task.update_status(A2ATaskStatus.FAILED)

        self._record_task(task)
        return task


    
    def _call_llm_for_analysis(self, symptoms: str, patient_history: Dict, prompt_data: Dict) -> Dict:
        """Call LLM to analyze symptoms using tools' prompt template"""
        try:
            system_prompt = prompt_data.get("system", "")
            user_prompt = prompt_data.get("user", "")

            if not system_prompt or not user_prompt:
                return {"conditions": [], "error": "No prompt template provided"}
            
            response = self._invoke_llm(system_prompt, user_prompt)
            logger.info(f"DEBUG: Raw LLM response: {response}")
            
            # STEP 1: Clean markdown FIRST
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip()
            
            logger.info(f"DEBUG: Cleaned response: {clean}")
            
            # STEP 2: Parse JSON (ONLY after cleaning)
            result = json.loads(clean)
            
            # STEP 3: Validate
            if "conditions" not in result:
                logger.warning(f"LLM response missing 'conditions' field. Got: {result.keys()}")
                result["conditions"] = []
            
            logger.info(f"DEBUG: Parsed {len(result.get('conditions', []))} conditions")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e}")
            return {"conditions": [], "error": str(e)}
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return {"conditions": [], "error": str(e)}



    def _call_llm_for_urgency(self, symptoms: str, patient_history: Dict, symptom_analysis: Dict, prompt_data: Dict) -> Dict:
        """Call LLM to classify urgency using tool's prompt template"""
        try:
            system_prompt = prompt_data.get("system", "")
            user_prompt = prompt_data.get("user", "")

            if not system_prompt or not user_prompt:
                return {"urgency_level": "UNKNOWN", "error": "No prompt template"}

            response = self._invoke_llm(system_prompt, user_prompt)
            
            # STEP 1: Clean markdown FIRST
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            clean = clean.strip()
            
            # STEP 2: Parse JSON (ONLY after cleaning)
            result = json.loads(clean)
            
            return result

        except json.JSONDecodeError as e:
            logger.error(f"LLM urgency JSON parse failed: {e}")
            return {"urgency_level": "UNKNOWN", "error": str(e)}
        except Exception as e:
            logger.error(f"LLM urgency failed: {e}")
            return {"urgency_level": "UNKNOWN", "error": str(e)}
        

    def _synthesize_recommendation(self, symptoms: str, patient_history: Dict, symptom_analysis: Dict, urgency: Dict) -> str:
        """Synthesize final recommendation using LLM"""
        conditions = symptom_analysis.get("conditions", [])
        urgency_reasoning = urgency.get("reasoning", "")
        urgency_level = urgency.get("urgency_level", "UNKNOWN")
        recommended_action = urgency.get("recommended_action", "")

        human_prompt = EXECUTOR_HUMAN_PROMPT.format(
            symptoms=symptoms,
            patient_history=json.dumps(patient_history),
            possible_conditions=json.dumps(conditions, indent=2),
            urgency_level=urgency_level,
            urgency_reasoning=urgency_reasoning,
            recommended_action=recommended_action
        )

        response = self._invoke_llm(EXECUTOR_SYSTEM_PROMPT, human_prompt)

        return response.strip()