import json
import logging
from typing import Dict, Any, Optional, List


from app.tools.base import MCPToolServer, MCPToolResult, MCPToolStatus, MCPToolDescriptor

from app.prompts import (
    URGENCY_CLASSIFICATION_SYSTEM_PROMPT,
    URGENCY_CLASSIFICATION_HUMAN_PROMPT,
    EMERGENCY_DISCLAIMER
)


logger = logging.getLogger(__name__)


class UrgencyClassifierTool(MCPToolServer):
    """
    MCP-complaint tool for urgency classification.
    PURE FUNCTION - NO LLM. Returns prompt template and validates response.
    The agent calls the LLM separately using these prompts.
    """

    def _register(self) -> MCPToolDescriptor:
        return MCPToolDescriptor(
            name="UrgencyClassifierTool",
            description="Classifies medical urgency level based on symptoms and patient history",
            version="1.0.0",
            input_schema={
                "type": "object",
                "properties": {
                    "symptoms": {"type": "string"},
                    "patient_history": {"type": "object"},
                    "possible_conditions": {"type": "array"}
                },

                "required": ["symptoms"]
            }
        )
    

    def get_prompt(self, symptoms: str, patient_history: Optional[Dict] = None, possible_conditions: Optional[List[Dict]] = None) -> Dict[str, str]:
        """
        Returns the prompt that the agent should send to LLM.
        tool doesn't call LLM - Just provides the prompt.
        """

        history_text = self._format_history(patient_history)
        conditions_text = self._format_conditions(possible_conditions)

        disclaimer = self._check_emergency_keywords(symptoms)

        user_prompt = URGENCY_CLASSIFICATION_HUMAN_PROMPT.format(
            symptoms=symptoms,
            patient_history=history_text,
            possible_conditions=conditions_text,
            disclaimer=disclaimer
        )


        return {
            "system": URGENCY_CLASSIFICATION_SYSTEM_PROMPT,
            "user": user_prompt
        }
    

    def validate_response(self, raw_response: str) -> Dict[str, Any]:
        """
        validates and parses LLM response.
        Returns cleaned JSON or error.
        """

        try:
            cleaned = self._clean_json(raw_response)
            parsed = json.loads(cleaned)

            required_fields = ["urgency_level", "confidence", "reasoning", "recommended_action"]
            for field in required_fields:
                if field not in parsed:
                    return {
                        "valid": False,
                        "error": f"Missing required field: {field}",
                        "raw": raw_response[:200]
                    }
                
            allowed_levels = ["ROUTINE", "SOON", "URGENT", "EMERGENCY"]

            if parsed["urgency_level"] not in allowed_levels:
                return {
                    "valid": False,
                    "error": f"Invalid urgency level. Must be one of {allowed_levels}",
                    "raw": raw_response[:200]
                }
            return {"valid": True, "data": parsed}
        

        except json.JSONDecodeError as e:
            return {"valid": False, "error": str(e), "raw": raw_response[:200]}


    def execute(self, symptoms: str, patient_history: Optional[Dict] = None,
                possible_conditions: Optional[List[Dict]] = None) -> MCPToolResult:
        """
        Tool execution - returns prompt template, NOT LLM result.
        The agent will call the LLM separately.
        """

        logger.info(f"UrgencyClassifierTool: Preparing urgency classification for symptoms: {symptoms[:50]}...")

        red_flags = self._detect_red_flags(symptoms)

        prompt = self.get_prompt(symptoms, patient_history, possible_conditions)

        return MCPToolResult(
            tool_name = "UrgencyClassifierTool",
            status = MCPToolStatus.SUCCESS,
            content={
                "prompt": prompt,
                "symptoms": symptoms,
                "red_flags": red_flags,
                "requires_llm": True
            },

            metadata={
                "symptoms_length": len(symptoms),
                "has_patient_history": patient_history is not None,
                "has_possible_conditions": possible_conditions is not None,
                "red_flags_detected": len(red_flags)
            }

        )
    

    def _format_history(self, patient_history: Optional[Dict]) -> str:
        """Format patient history for prompt"""

        if not patient_history:
            return "None Provided"

        parts = []

        if patient_history.get("conditions"):
            parts.append("Existing conditions: {', '.join(patient_history['conditions'])}")
        if patient_history.get("medications"):
            parts.append("Current medications: {', '.join(patient_history['medications'])}")
        if patient_history.get("allergies"):
            parts.append(f"Allergies: {', '.join(patient_history['allergies'])}")

        return "\n".join(parts) if parts else "None Provided"
    

    def _format_conditions(self, possible_conditions: Optional[List[Dict]]) -> str:
        """Format possible conditions for prompt"""

        if not possible_conditions:
            return "None Provided"
        
        lines = []

        for condition in possible_conditions[:5]:
            name = condition.get("name", "Unknown")
            confidence = condition.get("confidence", 0)
            lines.append(f"-{name} (confidence: {confidence})")

        return "\n".join(lines) if lines else "None Provided"
    

    def _detect_red_flags(self, symptoms: str) -> List[str]:
        """
        Detect emergency red flags in symptoms without LLM.
        Fast, rule-based check for immediate danger signs.
        """

        symptoms_lower = symptoms.lower()
        red_flags = []

        #Life threatening keywords

        emergency_keywords = {
            "chest pain": "Possible heart attack",
            "difficulty breathing": "Respiratory distress",
            "shortness of breath": "Respiratory distress",
            "severe bleeding": "Hemorrhage risk",
            "unconscious": "Loss of consciousness",
            "pass out": "Loss of consciousness",
            "stroke": "Possible stroke",
            "cannot speak": "Possible stroke",
            "face drooping": "Possible stroke",
            "severe headache": "Possible neurological emergency",
            "suicidal": "Psychiatric emergency",
            "overdose": "Drug overdose"
        }

        for keyword, warning in emergency_keywords.items():
            if keyword in symptoms_lower:
                red_flags.append(warning)
        
        return red_flags
    


    def _check_emergency_keywords(self, symptoms: str) -> str:
        """ Add emergency disclaimer if red flags detected"""
        red_flags = self._detect_red_flags(symptoms)
        if red_flags:
            return f"{EMERGENCY_DISCLAIMER} \n\n**RED FLAGS DETECTED:**\n-" + "\n-".join(red_flags)
        return ""
    

    def _clean_json(self, raw: str) -> str:
        """ Clean JSON from LLM response"""

        import re

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```\w*\n' ,'', cleaned)
            cleaned = re.sub(r'\n```$', '', cleaned)
        start = cleaned.find('{')
        end = cleaned.rfind('}')

        if start != -1 and end != -1:
            cleaned = cleaned[start:end+1]
        return cleaned