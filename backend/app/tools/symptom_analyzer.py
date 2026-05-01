import json
import logging
from typing import Dict, Any, Optional

from app.tools.base import MCPToolServer, MCPToolResult, MCPToolStatus, MCPToolDescriptor

from app.prompts import (
    SYMPTOM_ANALYSIS_SYSTEM_PROMPT,
    SYMPTOM_ANALYSIS_HUMAN_PROMPT,
    MEDICAL_DISCLAIMER
)

logger = logging.getLogger(__name__)


class SymptomAnalyzerTool(MCPToolServer):
    """
    MCP-compliant tool for symptom analysis.
    Pure Function - No LLM. Returns prompt template for validates response
    The agent calls the LLM separately using these prompts
    """

    def _register(self) -> MCPToolDescriptor:

        return MCPToolDescriptor(
            name="SymptomAnalyzerTool",
            description="Analyzes patient symptoms and provides potential diagnoses.",
            version="1.0",
            input_schema={
                "type": "object",
                "properties": {
                    "symptoms": {"type": "string"},
                    "patient_history": {"type": "object"}
                },
                "required": ["symptoms"]
            }

        )
    

    def get_prompt(self, symptoms: str, patient_history: Optional[Dict] = None) -> Dict[str, str]:
        """
        Returns the prompt that the agent should send to LLM
        Tool doesn't call LLM - just provides the prompt.
        """
        history_text = self._format_history(patient_history)

        return {
            "system": SYMPTOM_ANALYSIS_SYSTEM_PROMPT,
            "user": SYMPTOM_ANALYSIS_HUMAN_PROMPT.format(
                symptoms=symptoms,
                patient_history=history_text,
                disclaimer=MEDICAL_DISCLAIMER
            )
        }
    

    def validate_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Validates and parses the LLM response.
        Returns cleaned JSON or error.
        """

        try:
            cleaned = self._clean_json(raw_response)
            parsed = json.loads(cleaned)
            return {"valid": True, "data": parsed}
        except json.JSONDecodeError as e:
            return {"valid": False, "error": str(e), "raw": raw_response[:200]}
        


    def execute(self, symptoms: str, patient_history: Optional[Dict] = None) -> MCPToolResult:
        """
        Tool execution - returns prompt template, Not LLM result.
        The agent will call the LLM separately.
        """

        logger.info(f"SymptomAnalyzerTool called with symptoms: {symptoms} and patient_history: {patient_history}")

        prompt = self.get_prompt(symptoms, patient_history)

        return MCPToolResult(
            tool_name="SymptomAnalyzerTool",
            status=MCPToolStatus.SUCCESS,
            content={
                "prompt": prompt,
                "symptoms": symptoms,
                "requires_llm": True
            },
            metadata={
                "symptoms_length": len(symptoms),
                "has_patient_history": patient_history is not None
            }
        )
    

    def _format_history(self, patient_history: Optional[Dict]) -> str:
        """Format patient history for prompt"""

        if not patient_history:
            return "None provided"
        
        parts = []

        if patient_history.get("conditions"):
            parts.append(f"Existing conditions: {', '.join(patient_history['conditions'])}")

        if patient_history.get("medications"):
            parts.append(f"Current medications: {', '.join(patient_history['medications'])}")

        if patient_history.get("allergies"):
            parts.append(f"Allergies: {', '.join(patient_history['allergies'])}")

        return "\n".join(parts) if parts else "None provided"
    


    def _clean_json(self, raw: str) -> str:
        """Clean JSON from LLM response"""

        import re
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```\w*\n', '', cleaned)
            cleaned = re.sub(r'\n```$', '', cleaned)
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start != -1 and end != -1:
            cleaned = cleaned[start:end+1]

        return cleaned