import uuid
import uuid
import logging 
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from langchain_groq import ChatGroq
from app.config import config

logger = logging.getLogger(__name__)




class A2ATaskStatus(Enum):
    """Standard task lifecycle states """
    SUBMITTED = 'submitted'
    WORKING = 'working'
    COMPLETED = 'completed'
    FAILED = 'failed'


@dataclass
class A2ATask:
    """
    Task object - work unit passed between agents.
    Contains context, objective, and result.
    """

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    status: str = A2ATaskStatus.SUBMITTED
    objective: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


    def update_status(self, status: str):
        """Update task status and timestamp"""
        self.status = status
        self.updated_at = datetime.now().isoformat()
        
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "status": self.status,
            "objective": self.objective,
            "context": self.context,
            "result": self.result,
            "errors": self.errors,
            "created-at": self.created_at,
            "updated_at": self.updated_at
        }
    
@dataclass
class A2AAgentCard:
    """
    Agent Card - Declares agent identity and capabilities.
    Other agents use this to discover what this agent can do.
    """

    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    input_modes: List[str] = field(default_factory=list)
    output_modes: List[str] = field(default_factory=list)
    skills: List[Dict[str, Any]] = field(default_factory=list)
    endpoint: str = ""
    extensions: List[Dict[str, Any]] = field(default_factory=list)

    def  to_dict(self) -> Dict[str, Any]:
        result =  {
            "agent_id": self.agent_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "capabilities": self.capabilities,
            "input_modes": self.input_modes,
            "output_modes": self.output_modes,
            "skills": self.skills,
            "endpoint": self.endpoint
        }

        if self.extensions:
            result["capabilities"] = {
                "extensions": self.extensions
            }

        return result
    


#Base A2A Agent
class A2AAgent(ABC):
    """
    Base class for all A2A-compliant agents

    Every agent must:
    1. Register its capabilities via _register_card()
    2. Implement process-task() to handle incoming task.
    """

    def __init__(self):
        """
        LLM With retry + fallback support.
        """

        primary_llm = ChatGroq(
            model = config.PRIMARY_MODEL,
            api_key= config.GROQ_API_KEY,
            temperature=0.3,
            max_tokens=2000
        )

        fallback_llm = ChatGroq(
            model = config.FALLBACK_MODEL,
            api_key = config.GROQ_API_KEY,
            temperature=0.3,
            max_tokens=2000
        )

        self.llm = primary_llm.with_retry(
            retry_if_exception_type = (Exception,),
            stop_after_attempt = 3
        ).with_fallbacks([fallback_llm])

        self.agent_card = self._register_card()

        self.task_history: List[A2ATask] = []

        logger.info(f"A2A agent registered: {self.agent_card.name}")


    @abstractmethod
    def _register_card(self) -> A2AAgentCard:
        """Register agent capabilities. Must be overridden"""
        pass

    @abstractmethod
    def process_task(self, task: A2ATask):
        """Process an A2A task. Must be overriden"""
        pass

    def _invoke_llm(self, system: str, human: str) -> str:
        """Invoke LLM with system and human"""
        try:
            response = self.llm.invoke([
                {"role": "system", "content": system},
                {"role": "user", "content": human}
            ])
            return response.content

        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            raise


    def _record_task(self, task: A2ATask):
        """Store task in history for observability"""
        self.task_history.append(task)

    def get_task_history(self) -> List[Dict[str, Any]]:
        """ Get task history for debugging"""
        return [t.to_dict() for t in self.task_history]
