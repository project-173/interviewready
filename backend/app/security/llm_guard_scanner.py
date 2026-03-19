"""LLM Guard scanner service for input/output security."""

import subprocess
import sys
from typing import Optional, Tuple, List, Dict, Any
from ..core.logging import logger
from ..core.config import settings

HAS_LLM_GUARD = False
HAS_SPACY = False
_vault = None


def _ensure_spacy_models() -> bool:
    """Try to install missing spaCy models. Returns True if successful."""
    models = ["en_core_web_sm", "zh_core_web_sm"]

    for model in models:
        try:
            import spacy

            spacy.load(model)
            logger.info(f"SpaCy model already installed: {model}")
            continue
        except Exception:
            pass

        try:
            logger.info(f"Installing spaCy model: {model}...")
            result = subprocess.run(
                [sys.executable, "-m", "spacy", "download", model],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                logger.info(f"Successfully installed spaCy model: {model}")
            else:
                logger.warning(
                    f"Failed to install {model}: {result.stderr[:200] if result.stderr else 'Unknown error'}"
                )
        except Exception as e:
            logger.warning(f"Could not install {model}: {e}")

    try:
        import spacy

        spacy.load("en_core_web_sm")
        return True
    except Exception:
        return False


try:
    from llm_guard.input_scanners import PromptInjection, Anonymize
    from llm_guard.output_scanners import NoRefusal, Sensitive
    from llm_guard.vault import Vault as LLMGuardVault

    HAS_LLM_GUARD = True

    try:
        import spacy

        try:
            spacy.load("en_core_web_sm")
            spacy.load("zh_core_web_sm")
            HAS_SPACY = True
            logger.info("SpaCy models loaded successfully.")
        except Exception:
            logger.info("SpaCy models not found, attempting to install...")
            if _ensure_spacy_models():
                HAS_SPACY = True
                logger.info("SpaCy models installed and loaded.")
            else:
                HAS_SPACY = False
                logger.warning(
                    "Could not install spaCy models. Anonymize and Sensitive scanners disabled."
                )

    except ImportError:
        HAS_SPACY = False

except ImportError:
    HAS_LLM_GUARD = False
    HAS_SPACY = False


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
        self.enabled = getattr(settings, "LLM_GUARD_ENABLED", True) and HAS_LLM_GUARD
        if not HAS_LLM_GUARD:
            logger.warning("LLM Guard not installed. Security scanning disabled.")
        elif not self.enabled:
            logger.info("LLM Guard disabled via configuration.")
        else:
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
            scanner = PromptInjection()
            sanitized, is_valid, risk_score = scanner.scan(sanitized)

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

            if HAS_SPACY:
                try:
                    vault = get_vault()
                    if vault:
                        anonymizer = Anonymize(vault=vault, language="en")
                        sanitized, is_valid, risk_score = anonymizer.scan(sanitized)
                        if not is_valid:
                            issue = {
                                "scanner": "Anonymize",
                                "risk_score": risk_score,
                                "reason": "PII detected in input",
                            }
                            issues.append(issue)
                except Exception as e:
                    if (
                        "spacy" in str(e).lower()
                        or "zh_core" in str(e).lower()
                        or "download" in str(e).lower()
                    ):
                        logger.warning(
                            f"SpaCy Anonymize scanner failed, disabling spaCy scanners: {e}"
                        )
                        HAS_SPACY = False
                    else:
                        raise

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

            if HAS_SPACY:
                try:
                    sensitive_scanner = Sensitive()
                    sanitized, is_valid, risk_score = sensitive_scanner.scan(
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
                    if (
                        "spacy" in str(e).lower()
                        or "zh_core" in str(e).lower()
                        or "download" in str(e).lower()
                    ):
                        logger.warning(
                            f"SpaCy Sensitive scanner failed, disabling spaCy scanners: {e}"
                        )
                        HAS_SPACY = False
                    else:
                        raise

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
