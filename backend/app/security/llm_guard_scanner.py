"""LLM Guard scanner service for input/output security."""

import subprocess
import sys
from typing import Optional, Tuple, List, Dict, Any
from ..core.logging import logger
from ..core.config import settings

HAS_LLM_GUARD = False
HAS_SPACY = False
_vault = None

# Cached scanner instances (created once at startup)
_prompt_injection_scanner = None
_anonymizer_scanner = None
_refusal_scanner = None
_sensitive_scanner = None


def _preload_spacy_models() -> bool:
    """Pre-load spaCy models at startup. Returns True if successful."""
    try:
        import spacy

        # Pre-load both English and Chinese models
        spacy.load("en_core_web_sm")
        logger.info("Pre-loaded spaCy model: en_core_web_sm")

        spacy.load("zh_core_web_sm")
        logger.info("Pre-loaded spaCy model: zh_core_web_sm")

        return True
    except Exception as e:
        logger.warning(f"Failed to pre-load spaCy models: {e}")
        return False


# Pre-load spaCy models at module import time
_spacy_loaded = _preload_spacy_models()

try:
    from llm_guard.input_scanners import PromptInjection, Anonymize
    from llm_guard.output_scanners import NoRefusal, Sensitive
    from llm_guard.vault import Vault as LLMGuardVault

    HAS_LLM_GUARD = True
    HAS_SPACY = _spacy_loaded

    if HAS_SPACY:
        logger.info(
            "SpaCy models pre-loaded successfully - Anonymize and Sensitive scanners ACTIVE."
        )
    else:
        logger.warning(
            "SpaCy models not available - Anonymize and Sensitive scanners DISABLED."
        )

except ImportError:
    HAS_LLM_GUARD = False
    HAS_SPACY = False
    logger.warning("LLM Guard not installed. Security scanning disabled.")


def get_vault() -> Optional["LLMGuardVault"]:
    """Get or create the Vault instance for Anonymize scanner."""
    global _vault
    if _vault is None and HAS_LLM_GUARD:
        try:
            _vault = LLMGuardVault()
        except Exception as e:
            logger.warning(f"Failed to create Vault: {e}")
            _vault = None
    return _vault


class LLMGuardScanner:
    """Scanner for detecting prompt injection and sensitive content."""

    def __init__(self):
        global \
            _prompt_injection_scanner, \
            _anonymizer_scanner, \
            _refusal_scanner, \
            _sensitive_scanner, \
            HAS_SPACY

        self.enabled = getattr(settings, "LLM_GUARD_ENABLED", True) and HAS_LLM_GUARD

        if not HAS_LLM_GUARD:
            logger.warning("LLM Guard not installed. Security scanning disabled.")
        elif not self.enabled:
            logger.info("LLM Guard disabled via configuration.")
        else:
            logger.info("Initializing LLM Guard scanners...")

            # Create PromptInjection scanner once at startup
            _prompt_injection_scanner = PromptInjection()
            logger.info("Created PromptInjection scanner at startup")

            # Create Anonymize and Sensitive scanners once at startup (if spaCy available)
            if HAS_SPACY:
                vault = get_vault()
                if vault:
                    try:
                        _anonymizer_scanner = Anonymize(vault=vault, language="en")
                        _sensitive_scanner = Sensitive()
                        logger.info(
                            "Created Anonymize and Sensitive scanners at startup"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to create spaCy scanners: {e}")
                        HAS_SPACY = False

            # Create NoRefusal scanner once at startup
            _refusal_scanner = NoRefusal()
            logger.info("Created NoRefusal scanner at startup")

            logger.info("LLM Guard initialized for input/output scanning.")
            if HAS_SPACY:
                logger.info("SpaCy loaded - Anonymize and Sensitive scanners ACTIVE.")
            else:
                logger.warning(
                    "SpaCy not available - Anonymize and Sensitive scanners DISABLED."
                )

    def scan_input(self, prompt: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Scan user input for prompt injection and PII.

        Args:
            prompt: User input to scan

        Returns:
            Tuple of (is_safe, sanitized_prompt, list of issues)
        """
        global HAS_SPACY

        if not self.enabled:
            return True, prompt, [{"note": "scanner_disabled"}]

        issues = []
        sanitized = prompt

        try:
            # Use cached PromptInjection scanner
            sanitized, is_valid, risk_score = _prompt_injection_scanner.scan(sanitized)

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

            # Use cached Anonymize scanner if available
            if HAS_SPACY and _anonymizer_scanner:
                try:
                    sanitized, is_valid, risk_score = _anonymizer_scanner.scan(
                        sanitized
                    )
                    if not is_valid:
                        issue = {
                            "scanner": "Anonymize",
                            "risk_score": risk_score,
                            "reason": "PII detected in input",
                        }
                        issues.append(issue)
                except Exception as e:
                    logger.warning(f"Anonymize scanner failed: {e}")
                    HAS_SPACY = False

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
        global HAS_SPACY

        if not self.enabled:
            return True, output, [{"note": "scanner_disabled"}]

        issues = []
        sanitized = output

        try:
            # Use cached NoRefusal scanner
            sanitized, is_valid, risk_score = _refusal_scanner.scan("", sanitized)
            if not is_valid:
                issues.append(
                    {
                        "scanner": "NoRefusal",
                        "risk_score": risk_score,
                        "reason": "Refusal detected",
                    }
                )

            # Use cached Sensitive scanner if available
            if HAS_SPACY and _sensitive_scanner:
                try:
                    sanitized, is_valid, risk_score = _sensitive_scanner.scan(
                        "", sanitized
                    )
                    if not is_valid:
                        issues.append(
                            {
                                "scanner": "Sensitive",
                                "risk_score": risk_score,
                                "reason": "Sensitive content detected",
                            }
                        )
                except Exception as e:
                    logger.warning(f"Sensitive scanner failed: {e}")
                    HAS_SPACY = False

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
