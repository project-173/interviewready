"""LLM Guard scanner service for input/output security."""

from typing import Optional, Tuple, List, Dict, Any
from ..core.logging import logger
from ..core.config import settings

try:
    from llm_guard.input_scanners import PromptInjection
    from llm_guard.output_scanners import NoRefusal

    HAS_LLM_GUARD = True
except ImportError:
    HAS_LLM_GUARD = False


class LLMGuardScanner:
    """Scanner for detecting prompt injection and sensitive content."""

    def __init__(self):
        self.enabled = getattr(settings, "LLM_GUARD_ENABLED", True) and HAS_LLM_GUARD
        if not HAS_LLM_GUARD:
            logger.warning("LLM Guard not installed. Security scanning disabled.")
        elif not self.enabled:
            logger.info("LLM Guard disabled via configuration.")
        else:
            logger.info("LLM Guard initialized for input/output scanning.")

    def scan_input(self, prompt: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Scan user input for prompt injection.

        Args:
            prompt: User input to scan

        Returns:
            Tuple of (is_safe, sanitized_prompt, list of issues)
        """
        if not self.enabled:
            return True, prompt, [{"note": "scanner_disabled"}]

        try:
            scanner = PromptInjection()
            sanitized, is_valid, risk_score = scanner.scan(prompt)

            if not is_valid:
                issue = {
                    "scanner": "PromptInjection",
                    "risk_score": risk_score,
                    "reason": "Potential prompt injection detected",
                }
                logger.security_event(
                    "prompt_injection_detected", risk_score=risk_score, issue=issue
                )
                return False, sanitized, [issue]

            return True, sanitized, []

        except Exception as e:
            logger.error(f"LLM Guard input scan failed: {e}")
            return True, prompt, []

    def scan_output(self, output: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Scan model output for sensitive information and refusals.

        Args:
            output: Model output to scan

        Returns:
            Tuple of (is_safe, sanitized_output, list of issues)
        """
        if not self.enabled:
            return True, output, [{"note": "scanner_disabled"}]

        issues = []
        sanitized = output

        try:
            refusal_scanner = NoRefusal()
            sanitized, is_valid, risk_score = refusal_scanner.scan("", sanitized)
            if not is_valid:
                issues.append(
                    {
                        "scanner": "NoRefusal",
                        "risk_score": risk_score,
                        "reason": "Refusal detected",
                    }
                )

            if issues:
                logger.security_event(
                    "output_sensitive_detected", risk_count=len(issues), issues=issues
                )
                return False, sanitized, issues

            return True, sanitized, []

        except Exception as e:
            logger.error(f"LLM Guard output scan failed: {e}")
            return True, output, []

    def scan_both(
        self, input_text: str, output_text: str
    ) -> Tuple[bool, bool, List[Dict[str, Any]]]:
        """Scan both input and output.

        Args:
            input_text: User input
            output_text: Model output

        Returns:
            Tuple of (input_safe, output_safe, all_issues)
        """
        input_safe, _, input_issues = self.scan_input(input_text)
        output_safe, _, output_issues = self.scan_output(output_text)

        return input_safe, output_safe, input_issues + output_issues


_llm_guard_scanner: Optional[LLMGuardScanner] = None


def get_llm_guard_scanner() -> LLMGuardScanner:
    """Get or create the global LLM Guard scanner instance."""
    global _llm_guard_scanner
    if _llm_guard_scanner is None:
        _llm_guard_scanner = LLMGuardScanner()
    return _llm_guard_scanner
