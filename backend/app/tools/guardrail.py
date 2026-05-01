import re
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime


from app.tools.base import MCPToolServer, MCPToolDescriptor, MCPToolResult, MCPToolStatus
from app.prompts import MEDICAL_DISCLAIMER

logger = logging.getLogger(__name__)


class GuardrailTool(MCPToolServer):
    """
    MCP-complaint tool for medical safety guardrails.
    PURE FUNCTION - NO LLM. Scans content for dangerous patterns
    """

    # Dangerous patterns that must be blocked
    DANGEROUS_PATTERNS = [
        (r"stop taking your medication", "BLOCK - Medication advice"),
        (r"ignore your doctor", "BLOCK - Contradicts medical advice"),
        (r"you definitely have", "FLAG - Overconfident diagnosis"),
        (r"guarantee.*cure", "BLOCK - False guarantee"),
        (r"100%.*sure", "FLAG - Overconfident"),
        (r"no need to see a doctor", "BLOCK - Dangerous advice"),
        (r"treat yourself with", "FLAG - Self-treatment advice"),
        (r"buy.*from this link", "BLOCK - Commercial promotion"),
    ]


    WARNING_PATTERNS = [
        (r"probably", "WARNING - Uncertainty"),
        (r"might be", "WARNING - Speculative"),
        (r"suggest", "WARNING - Recommendation"),
        (r"could be", "WARNING - Speculative"),
    ]


    DISCLAIMER_KEYWORDS = [
        "not medical advice",
        "consult a physician",
        "see a doctor",
        "healthcare professional",
        "informational purposes"
    ]


    def _register(self) -> MCPToolDescriptor:
        return MCPToolDescriptor(
            name="GuardrailTool",
            description="Scans medical recommendation for safety violations and adds disclaimer",
            version="1.0.0",
            input_schema = {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "strict_mode": {"type": "boolean", "default": True},
                    "add_disclaimer": {"type": "boolean", "default": True}
                },
                "required": ["content"]
            }
        )
    

    def execute(self, content: str, strict_mode: bool = True, add_disclaimer: bool = True) -> MCPToolResult:
        """
        Scan  content for safety violations.
        Returns:
            - blocked: True if content should not be shown
            - Violations: List of violations found
            - warnings: List of warnings found
            - Sanitized_content: content with violations removed/modified
        """

        logger.info(f"GuardrailTool: scanning content of length {len(content)}")
        content_lower = content.lower()
        violations = []

        warnings = []

        # Step 1: Scan for dangerous patterns
        for pattern, message in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content_lower):
                violations.append({
                    "type": "DANGEROUS",
                    "pattern": pattern,
                    "message": message,
                    "action": "BLOCK"
                })

        # Step 2: Scan for warning patterns
        for pattern, message in self.WARNING_PATTERNS:
            if re.search(pattern, content_lower):
                warnings.append({
                    "type": "WARNING",
                    "pattern": pattern,
                    "message": message,
                    "action": "FLAG"
                })

        # Step 3: Check for disclaimer
        has_disclaimer = any(keyword in content_lower for keyword in self.DISCLAIMER_KEYWORDS)


        if not has_disclaimer and add_disclaimer:
            warnings.append({
                "type": "MISSING_DISCLAIMER",
                "message": "Response missing medical disclaimer",
                "action": "ADD"
            })

        # Step 4: Determine if content should be blocked

        dangerous_violations = [v for v in violations if v["type"] == "DANGEROUS"]
        blocked = len(dangerous_violations) > 0

        # Step 5: Sanitize content
        sanitized_content = content

        if blocked and strict_mode:
            sanitized_content = self._get_blocked_message(violations)

            logger.warning(f"GuardrailTool: BLOCKED content due to {len(dangerous_violations)} violations")

        else:
            if not has_disclaimer and add_disclaimer:
                sanitized_content = self._add_disclaimer(content)
                logger.info("GuardrailTool: Added disclaimer to content")

        passed = not blocked

        status = MCPToolStatus.SUCCESS if passed else MCPToolStatus.WARNING

        return MCPToolResult(
            tool_name="GuardrailTool",
            status=status,
            content={
                "passed": passed,
                "blocked": blocked,
                "violations": violations,
                "warnings": warnings,
                "sanitized_content": sanitized_content,
                "disclaimer_added": not has_disclaimer and add_disclaimer
            },

            metadata={
                "original_length": len(content),
                "sanitized_length": len(sanitized_content),
                "violations_count": len(violations),
                "warnings_count": len(warnings),
                "strict_mode": strict_mode,
                "timestamp": datetime.now().isoformat()
            }
        )
    


    def _add_disclaimer(self, content: str) -> str:
        """ Add medical disclaimer to content"""
        return f"{content}\n\n{MEDICAL_DISCLAIMER}"
    

    def _get_blocked_message(self, violations: List[Dict]) -> str:
        """
        Get safe message when content is blocked
        """
        violation_message = [v["message"] for v in violations if v["type"] == "DANGEROUS"]

        block_message = """
        I cannot provide the response you requested because it contains potentially harmful medical advice.
        **Safety violations detected**
    """+ "\n-".join(violation_message) + f"""

    {MEDICAL_DISCLAIMER}
    Please consult a qualified healthcare professional for medical advice.
    """

        return block_message.format(MEDICAL_DISCLAIMER=MEDICAL_DISCLAIMER)
    

    def quick_check(self, content: str) -> Tuple[bool, List[str]]:
        """
        Quick check for dangerous content (lightweight version).
        Returns (is_safe, list_of_violations)
        """
        content_lower = content.lower()

        violations = []

        for pattern, message in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content_lower):
                violations.append(message)
        return len(violations) == 0, violations
    

    def requires_disclaimer(self, content: str) -> bool:
        """ Check if content needs a disclaimer"""
        content_lower = content.lower()
        return not any(keyword in content_lower for keyword in self.DISCLAIMER_KEYWORDS)