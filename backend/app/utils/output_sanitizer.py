"""Output sanitizer for detecting and removing system prompt leakage."""

import re
from typing import Tuple, List, Dict, Any
from ..core.logging import logger


class OutputSanitizer:
    """Sanitize model output to detect system prompt leakage and other issues."""

    SYSTEM_PROMPT_PATTERNS = [
        r"(?i)(system\s*prompt|instruction|sys_prompt)",
        r"(?i)(you\s*are\s*a|you\s*are\s*an)\s+(language\s*model|AI|assistant|chatbot)",
        r"(?i)(ignore\s+(all\s+)?previous|from\s+the\s+start)",
        r"(?i)(disregard|forget)\s+(all\s+)?(previous|your|instruct)",
        r"(?i)(new\s+instruction|additional\s+instruction)",
        r"(?i)(#+\s*)?(system|instruction|persona|behavior)",
        r"(?i)(do\s+not\s+reveal|tell\s+me\s+your|what\s+are\s+your)\s*(prompt|instruction|system)",
        r"<(?:system|instruction|prompt)[^>]*>.*?</(?:system|instruction|prompt)>",
        r"(?i)(SKIP|IGNORE)\s*(THIS|PREVIOUS|ALL)?",
        r"(?i)^(SYSTEM|INSTRUCTIONS|COMMAND):",
    ]

    DANGEROUS_PATTERNS = [
        r"(?i)(sudo|exec|eval|compile)\s*\(",
        r"(?i)<script[^>]*>.*?</script>",
        r"\x1b\[[0-9;]*[a-zA-Z]",
    ]

    def __init__(self):
        self.system_patterns = [
            re.compile(p, re.DOTALL) for p in self.SYSTEM_PROMPT_PATTERNS
        ]
        self.dangerous_patterns = [
            re.compile(p, re.DOTALL) for p in self.DANGEROUS_PATTERNS
        ]

    def sanitize(self, output: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Sanitize output and detect system prompt leakage.

        Args:
            output: Model output to sanitize

        Returns:
            Tuple of (is_safe, sanitized_output, list of issues)
        """
        issues = []
        sanitized = output

        for i, pattern in enumerate(self.system_patterns):
            matches = pattern.findall(sanitized)
            if matches:
                issues.append(
                    {
                        "type": "system_prompt_leakage",
                        "pattern_index": i,
                        "matches": len(matches),
                        "severity": "HIGH",
                    }
                )

        for i, pattern in enumerate(self.dangerous_patterns):
            matches = pattern.findall(sanitized)
            if matches:
                issues.append(
                    {
                        "type": "dangerous_content",
                        "pattern_index": i,
                        "matches": len(matches),
                        "severity": "CRITICAL",
                    }
                )

        if issues:
            logger.security_event(
                "output_sanitization_issues",
                issue_count=len(issues),
                issues=issues,
                output_length=len(output),
            )
            return False, sanitized, issues

        return True, sanitized, []

    def check_basic(self, output: str) -> bool:
        """Quick check if output appears safe without full sanitization.

        Args:
            output: Output to check

        Returns:
            True if no obvious issues detected
        """
        for pattern in self.system_patterns[:5]:
            if pattern.search(output):
                return False
        return True


_output_sanitizer = None


def get_output_sanitizer() -> OutputSanitizer:
    """Get or create the global output sanitizer instance."""
    global _output_sanitizer
    if _output_sanitizer is None:
        _output_sanitizer = OutputSanitizer()
    return _output_sanitizer
