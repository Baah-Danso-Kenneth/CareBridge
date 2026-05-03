from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from .base import MemoryBase


logger = logging.getLogger(__name__)



class EpisodicMemory(MemoryBase):
    """
    Episodic memory for patient interactions.
        Stores interactions as episodes, allowing retrieval of past interactions based on context.
        Each episode can contain multiple interactions, and the memory can be queried for relevant episodes.
        This is useful for maintaining a history of patient interactions and retrieving relevant information when needed.
    """

    def __init__(self, patient_id: str):
        """
        Initialize episodic memory for a specific patient.

        Args:
           patient_id:  Unique identifier for the patient.
        """

        self.patient_id = patient_id
        self.memory_file = Path(__file__).parent.parent.parent / "data" / f"episodic_{patient_id}.json"

        self.data = self._load()
        logger.info(f"EpisodicMemory initialized for patient: {patient_id}")


    def _load(self) -> Dict[str, Any]:
        """Load memory from file, create default if not  exist"""
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)

            if self.memory_file.exists():
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            else:
                default_data = {
                    "patient_id":self.patient_id,
                    "session_history": [],
                    "past_recommendations": [],
                    "preferences": {},
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }

                self._save(default_data)
                return default_data


        except Exception as e:
            logger.error(f"Failed to load episodic memory: {e}")
            return {
                "patient_id": self.patient_id,
                "session_history": [],
                "past_recommendations":[],
                "preferences": {},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }



    def _save(self, data: Dict[str, Any] = None):
        """Save memory to file """
        try:
            if data is None:
                data = self.data
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.data = data
        except Exception as e:
            logger.error(f"Failedto save episodic memory: {e}")



    def add_session(self, symptoms: str, urgency_level: str, recommendation: str, score: float = None):
        """Record a triage session"""
        session = {
            "timestamp": datetime.now().isoformat(),
            "symptoms": symptoms[:200],
            "urgency_level": urgency_level,
            "recommendation": recommendation[:300],
            "score": score
        }

        self.data["session_history"].append(session)

        if len(self.data["session_history"]) > 20:
            self.data["session_history"] = self.data["session_history"][-20:]

        self._save()
        logger.info(f"Added session for patient {self.patient_id}")



    def get_recent_sessions(self, limit: int= 5) -> List[Dict]:
        """Get most recent sessions"""
        return self.data.get("session_history", [])[-limit:]

    def get_preferences(self) -> Dict[str, Any]:
        """Get patient preferences"""
        return self.data.get("preferences", {})


    
    def store(self, key: str, value: Any) -> bool:
        """Store arbitrary key-value pair"""
        self.data[key] = value
        self._save()
        return True

    

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve by key"""
        return self.data.get(key)


    def update(self, key: str, value: Any) -> bool:
        """Update existing data """
        if key in self.data:
            self.data[key] = value
            self._save()
            return True

        return False


    def delete(self, key: str) -> bool:
        """Delete from memory"""
        if key in self.data:
            del self.data[key]
            self._save()
            return True

        return False