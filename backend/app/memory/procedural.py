import logging
from typing import Dict, Any, Optional
from app.memory.base import MemoryBase

logger = logging.getLogger(__name__)


class ProceduarlMemory(MemoryBase):
    """
    Procedural Memory for clinical guidelines and rules.

    Stores:
    - Safety rules
    - Urgency classification guidelines
    - Disclaimer requirements
    - Follow-up protocols
    """

    def __init__(self):
        self.rules = self._load_rules()
        logger.info("ProceduarlMemory initialized")

    def _load_rules(self):
        """Load Proceduarl rules"""
        return {
            #Safety rules
            "safety":"""
                NEVER:
                - Diagnose specific conditions
                - Guarantee doctor's advice
                - Contradict doctor's advicce
                - Recommend stopping medications

                ALWAYS:
                - Add medical disclaimer
                - Recommend seeing a doctor for serious symptoms
                - Flag emergency symptoms immediately

                """,

            "urgency": """
                EMERGENCY (Immediate):
                - Chest Pain
                - Difficulty breathing
                - Severe bleeding
                - Loss of consciousness
                - Stroke symptoms

                URGENT (24 hours):
                - High fever (>103F)
                - Severe pain
                - Persistent vomitting
                - Signs of infection

                SOON (1-3 days)
                - Moderate fever
                - Persistent cough
                - Fatigue
                - Mild pain


                ROUTINE (1-2 weeks):
                - Mild symptoms
                - Follow-up visits
                - Medication reviews
            """,

            "follow_up": """
                - EMERGENCY: Follow up within 24 hours
                - URGENT: Follow up within 3 days
                - SOON: Follow up within 1 week
                - ROUTINE: Follow up within 2 weeks
            """,

            "disclaimer": """
                This information is for educational purposes only.
                Not medical advice. Consulta healthcare professional
            """
        }
    

    def get_rule(self, rule_name: str) -> str:
        """Get a specific rule"""
        return self.rules.get(rule_name, "")
    

    def get_all_rules(self) ->str:
        """Get all rules as formatted string"""
        return "\n\n".join([f"==={k.upper()} ===\n{v}" for k, v in self.rules.items()])
    
    def get_prompt_injection(self, context: str="safety")  ->str:
        """Get formatted rules fro prompt injection"""
        return f"""
                PROCEDURAL MEMORY - CLINICAL GUIDELINES:
                {self.get_rule(context)}

                FOLLOW THESE GUIDELINES CAREFULLY.
                """
    # Core memory interface

    def store(self, key: str, value: Any) ->bool:
        self.rules[key] = value
        return True
    
    def retrieve(self, key: str) -> Optional[Any]:
        return self.get_rule(key)
    

    def update(self, key: str, value: Any) ->bool:
        return self.store(key, value)
    

    def delete(self, key: str) -> bool:
        if key in self.rules:
            del self.rules[key]
            return True
        return False
