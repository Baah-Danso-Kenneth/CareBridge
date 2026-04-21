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


class UrgencyClassifier(MCPToolServer):
    pass