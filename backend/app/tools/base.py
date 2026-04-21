from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime



class MCPToolStatus(Enum):
    """Enumeration of possible statuses for an MCP tool."""
    SUCCESS="success"
    ERROR="error"
    WARNING="warning"


@dataclass
class MCPToolResult:
    """Structure to hold the result of an MCP tool execution."""
    tool_name: str
    status: MCPToolStatus
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "status": self.status.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


@dataclass
class MCPToolDescriptor:
    """Provides description and usage information for an MCP tool."""
    name: str
    description: str
    version: str
    input_schema: Dict[str, Any]


class MCPToolServer:
    """ Base class for MCP tool servers. Each tool should implement the executed method to define its behavior."""

    def __init__(self):
        self.descriptor = self._register()


    def _register(self) -> MCPToolDescriptor:
        raise NotImplementedError("Each MCP tool must implement the _register method to provide its descriptor.")

    
    def execute(self, **kwargs) -> MCPToolResult:
        raise NotImplementedError("Each MCP tool must implement the execute method to define its behavior.")
    
    
    def __call__(self, **kwargs) -> MCPToolResult:
        result = self.execute(**kwargs)
        return result.to_dict()
    
