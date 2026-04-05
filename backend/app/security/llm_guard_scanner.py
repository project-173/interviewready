"""LLM Guard scanner service for input/output security."""

from typing import Optional, Tuple, List, Dict, Any
from ..core.logging import logger
from ..core.config import settings

HAS_LLM_GUARD = False

# Cached scanner instances (created once at startup)
# LLM Guard scanners:
_prompt_injection_scanner = None
_refusal_scanner = None


# NOT LLM GUARD - DataFog for PII detection
# DataFog is used instead of LLM Guard's Anonymize/Sensitive scanners
import datafog as DataFog


try:
    # LLM Guard: Only import PromptInjection and NoRefusal
    # Anonymize and Sensitive are replaced by DataFog
    from llm_guard.input_scanners import PromptInjection  # LLM Guard
    from llm_guard.output_scanners import NoRefusal  # LLM Guard

    HAS_LLM_GUARD = True
    logger.info("LLM Guard loaded (PromptInjection, NoRefusal)")

except ImportError:
    HAS_LLM_GUARD = False
    logger.warning("LLM Guard not installed. Security scanning disabled.")


class LLMGuardScanner:
    """Scanner for detecting prompt injection and sensitive content."""

    def __init__(self):
        global _prompt_injection_scanner, _refusal_scanner

        self.enabled = getattr(settings, "LLM_GUARD_ENABLED", True) and HAS_LLM_GUARD

        if not HAS_LLM_GUARD:
            logger.warning("LLM Guard not installed. Security scanning disabled.")
        elif not self.enabled:
            logger.info("LLM Guard disabled via configuration.")
        else:
            logger.info("Initializing security scanners...")

            # LLM Guard: PromptInjection scanner (input) - detects prompt injection attacks
            _prompt_injection_scanner = PromptInjection()
            logger.info("Created PromptInjection scanner at startup")  # LLM Guard

            # LLM Guard: NoRefusal scanner (output) - detects model refusals
            _refusal_scanner = NoRefusal()
            logger.info("Created NoRefusal scanner at startup")  # LLM Guard

            logger.info("Security scanners initialized (PromptInjection, NoRefusal)")

    def scan_input(self, prompt: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Scan user input for prompt injection and PII.

        Args:
            prompt: User input to scan

        Returns:
            Tuple of (is_safe, sanitized_prompt, list of issues)
        """
        if not self.enabled:
            return True, prompt, [{"note": "scanner_disabled"}]

        issues = []
        sanitized = prompt

        try:
            # LLM Guard: Scan for prompt injection attacks
            sanitized, is_valid, risk_score = _prompt_injection_scanner.scan(sanitized)

            if not is_valid:
                issue = {
                    "scanner": "PromptInjection",  # LLM Guard
                    "risk_score": risk_score,
                    "reason": "Potential prompt injection detected",
                }
                logger.security_event(
                    "prompt_injection_detected", risk_score=risk_score, issue=issue
                )
                return False, sanitized, [issue]

            # NOT LLM GUARD - DataFog with regex engine for PII detection in input
            # DataFog.scan_prompt() scans user input for PII (emails, phones, SSN, etc.)
            # Using regex engine (~1 MB) instead of spaCy to avoid large model downloads
            try:
                datafog_result = DataFog.scan_prompt(sanitized, engine="regex")
                if datafog_result.entities:
                    # Redact PII using DataFog
                    sanitized = DataFog.sanitize(sanitized, engine="regex")
                    issue = {
                        "scanner": "DataFog",  # NOT LLM GUARD
                        "risk_score": min(len(datafog_result.entities) / 10, 1.0),
                        "reason": f"PII detected in input ({len(datafog_result.entities)} entities)",
                    }
                    issues.append(issue)
            except Exception as e:
                logger.warning(f"DataFog PII scan failed: {e}")

            return True, sanitized, issues

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
            # LLM Guard: Scan for model refusals
            sanitized, is_valid, risk_score = _refusal_scanner.scan("", sanitized)
            if not is_valid:
                issues.append(
                    {
                        "scanner": "NoRefusal",  # LLM Guard
                        "risk_score": risk_score,
                        "reason": "Refusal detected",
                    }
                )

            # NOT LLM GUARD - DataFog with regex engine for PII detection in output
            # DataFog.filter_output() scans model output for PII
            # Using regex engine (~1 MB) instead of spaCy to avoid large model downloads
            try:
                datafog_result = DataFog.filter_output(sanitized, engine="regex")
                if datafog_result.entities:
                    # Redact PII using DataFog
                    sanitized = datafog_result.redacted_text
                    issue = {
                        "scanner": "DataFog",  # NOT LLM GUARD
                        "risk_score": min(len(datafog_result.entities) / 10, 1.0),
                        "reason": f"Sensitive content detected in output ({len(datafog_result.entities)} entities)",
                    }
                    issues.append(issue)
            except Exception as e:
                logger.warning(f"DataFog output scan failed: {e}")

            if issues:
                logger.security_event(
                    "output_sensitive_detected",
                    risk_count=len(issues),
                    issues=issues,
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
