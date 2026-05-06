import logging
import requests
from typing import Dict, Any, List, Optional
from app.tools.base import MCPToolServer, MCPToolResult, MCPToolStatus, MCPToolDescriptor
from app.config import config

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

    def execute(self, patient_id: str, fhir_token: Optional[str] = None, fhir_url: Optional[str]=None) -> MCPToolResult:
        logger.info(f"PatientHistoryTool: fetching data for patient_id: {patient_id}")

        conditions = []
        medications = []
        allergies = []
        source = "mock"


        if config.FHIR_ENABLED:
            try:
                headers = {}
                if fhir_token:
                    headers["Authorization"] = f"Bearer {fhir_token}"
                
                base_url= fhir_url or config.FHIR_BASE_URL
                conditions_url = f"{base_url}/Condition?patient={patient_id}"
                logger.debug(f"Fetching conditions: {conditions_url}")

                response = requests.get(
                    conditions_url,
                    headers=headers,
                    timeout=config.FHIR_TIMEOUT
                )

                if response.status_code == 200:
                    data = response.json()
                    for entry in data.get("entry", []):
                        resource = entry.get("resource", {})
                        code = resource.get("code", {})


                        condition_name = code.get("text")

                        if not condition_name:
                            coding = code.get("coding", [])
                            if coding:
                                condition_name = coding[0].get("display","")

                        if condition_name:
                            conditions.append(condition_name)

                    if conditions:
                        source = "fhir"
                        logger.info(f"Found {len(conditions)} from FHIR")
        
                else:
                    logger.warning(f"FHIR returned status {response.status_code}")

            except requests.exceptions.Timeout:
                logger.warning(f"FHIR timeout after {config.FHIR_TIMEOUT}'s")

            except requests.exceptions.ConnectionError:
                logger.warning(f"FHIR connection errror to {config.FHIR_TIMEOUT}")

            except Exception as e:
                logger.warning(f"FHIR request failed: {e}")


        if not conditions:
            logger.info(f"Using mock data for patient {patient_id}")

            mock_patients = {
                "example": {
                    "conditions": [""],
                    "medications": [""],
                    "allergies": [""]
                },
                "smart-123": {

                },

                "default": {

                }
            }

            mock = mock_patients.get(patient_id, mock_patients["default"])
            conditions = mock["conditions"]
            medications = mock["medications"]
            allergies = mock["allergies"]
            source = "mock"

        
        return MCPToolResult(
            tool_name="PatientHistoryTool",
            status=MCPToolStatus.SUCCESS,
            content= {
                "conditions": conditions,
                "medications": medications,
                "allergies": allergies,
                "patient_id": patient_id,
                "source": source
            },
            metadata={
                "conditions": conditions,
                "medications": medications,
                "data_source": source,
                "fhir_enabled": config.FHIR_ENABLED
            }
        )
    
    