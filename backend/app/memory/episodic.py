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


    