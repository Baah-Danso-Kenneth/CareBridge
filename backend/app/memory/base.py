from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class MemoryBase(ABC):
    """
    Base class for all memory systems
    """

    @abstractmethod
    def store(self, key: str, value: Any) -> bool:
        """
        Store data in memory"""
        pass

    @abstractmethod
    def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieve data from memory"""
        pass

    @abstractmethod
    def update(self, key: str, value: Any) -> bool:
        """
        Update existing data in memory"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete data from memory"""
        pass

    