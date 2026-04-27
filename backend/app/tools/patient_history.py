import logging
from typing import Dict, Any, List
from app.tools.base import MCPToolServer, MCPToolResult, MCPToolStatus, MCPToolDescriptor

logger = logging.getLogger(__name__)


class PatientHistoryTool(MCPToolServer):

    def _register(self) -> MCPToolDescriptor:
        return MCPToolDescriptor(
            name="PatientHistoryTool",
            description="Retrieves the medical history of a patient based on their ID.",
            version="1.0",
            input_schema={
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                    "fhir_token": {"type": "string"}
                },
                "required": ["patient_id"]
            }
        )

    def execute(self, patient_id: str, fhir_token: str = None) -> MCPToolResult:
        logger.info(f"PatientHistoryTool: fetching data for patient_id: {patient_id}")

        mock_data = {
            "conditions": ["Hypertension", "Type 2 Diabetes"],
            "medications": ["Lisinopril 10mg", "Metformin 500mg"],
            "allergies": ["Penicillin"],
            "patient_id": patient_id
        }
        
        return MCPToolResult(
            tool_name=self.descriptor.name,
            status=MCPToolStatus.SUCCESS,
            content=mock_data,
            metadata={"source": "mock_fhir", "patient_id": patient_id}
        )
    
    