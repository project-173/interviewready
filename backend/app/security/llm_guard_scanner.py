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
    model = "en_core_web_sm"

    try:
        import spacy
        spacy.load(model)
        logger.info(f"SpaCy model already installed: {model}")
        return True
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
            return False
    except Exception as e:
        logger.warning(f"Could not install {model}: {e}")
        return False

    try:
        import spacy
        spacy.load(model)
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
            HAS_SPACY = True
            logger.info("SpaCy en_core_web_sm model loaded successfully.")
        except Exception:
            logger.info("SpaCy model not found, attempting to install...")
            if _ensure_spacy_models():
                HAS_SPACY = True
                logger.info("SpaCy model installed and loaded.")
            else:
                HAS_SPACY = False
                logger.warning(
                    "Could not install spaCy model. Anonymize and Sensitive scanners disabled."
                )

    except ImportError:
        HAS_SPACY = False

except ImportError:
    HAS_LLM_GUARD = False
    HAS_SPACY = False

def get_vault() -> Optional["LLMGuardVault"]:
    """Get or create the Vault instance for Anonymize scanner (singleton)."""
    global _vault
    if _vault is None and HAS_LLM_GUARD:
        try:
            _vault = LLMGuardVault()
        except Exception as e:
            logger.warning(f"Failed to create Vault: {e}")
            _vault = None
    return _vault

class LLMGuardScanner:
    """Scanner for detecting prompt injection and sensitive content.

    Scanners are instantiated ONCE in __init__ and reused across all calls.
    Previously, scanners were created inside scan_input/scan_output on every
    request, which re-loaded the underlying transformer models each time and
    caused memory to balloon well past 2 GB.
    """

    def __init__(self):
        self.enabled = getattr(settings, "LLM_GUARD_ENABLED", True) and HAS_LLM_GUARD

        self._prompt_injection: Optional["PromptInjection"] = None
        self._anonymizer: Optional["Anonymize"] = None
        self._no_refusal: Optional["NoRefusal"] = None
        self._sensitive: Optional["Sensitive"] = None

        if not HAS_LLM_GUARD:
            logger.warning("LLM Guard not installed. Security scanning disabled.")
            return

        if not self.enabled:
            logger.info("LLM Guard disabled via configuration.")
            return

        logger.info("LLM Guard initialising scanners (loaded once at startup)...")

        try:
            self._prompt_injection = PromptInjection()
            logger.info("PromptInjection scanner loaded.")
        except Exception as e:
            logger.error(f"Failed to load PromptInjection scanner: {e}")

        try:
            self._no_refusal = NoRefusal()
            logger.info("NoRefusal scanner loaded.")
        except Exception as e:
            logger.warning(f"Failed to load NoRefusal scanner: {e}")

        if HAS_SPACY:
            vault = get_vault()
            if vault:
                try:
                    self._anonymizer = Anonymize(vault=vault, language="en")
                    logger.info("Anonymize scanner loaded.")
                except Exception as e:
                    logger.warning(f"Failed to load Anonymize scanner: {e}")

            try:
                self._sensitive = Sensitive()
                logger.info("Sensitive scanner loaded.")
            except Exception as e:
                logger.warning(f"Failed to load Sensitive scanner: {e}")
        else:
            logger.warning("SpaCy not available — Anonymize and Sensitive scanners disabled.")

        logger.info("LLM Guard scanner initialisation complete.")

    def scan_input(self, prompt: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Scan user input for prompt injection and PII.

        Returns:
            (is_safe, sanitized_prompt, list_of_issues)
        """
        if not self.enabled:
            return True, prompt, [{"note": "scanner_disabled"}]

        issues: List[Dict[str, Any]] = []
        sanitized = prompt

        if self._prompt_injection is not None:
            try:
                sanitized, is_valid, risk_score = self._prompt_injection.scan(sanitized)
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
            except Exception as e:
                logger.error(f"PromptInjection scan error: {e}")

        if self._anonymizer is not None:
            try:
                sanitized, is_valid, risk_score = self._anonymizer.scan(sanitized)
                if not is_valid:
                    issues.append({
                        "scanner": "Anonymize",
                        "risk_score": risk_score,
                        "reason": "PII detected in input",
                    })
            except Exception as e:
                logger.warning(f"Anonymize scan error (skipping): {e}")

        return True, sanitized, issues

    def scan_output(self, output: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """Scan model output for refusals and sensitive information.

        Returns:
            (is_safe, sanitized_output, list_of_issues)
        """
        if not self.enabled:
            return True, output, [{"note": "scanner_disabled"}]

        issues: List[Dict[str, Any]] = []
        sanitized = output

        if self._no_refusal is not None:
            try:
                sanitized, is_valid, risk_score = self._no_refusal.scan("", sanitized)
                if not is_valid:
                    issues.append({
                        "scanner": "NoRefusal",
                        "risk_score": risk_score,
                        "reason": "Refusal detected",
                    })
            except Exception as e:
                logger.warning(f"NoRefusal scan error (skipping): {e}")

        if self._sensitive is not None:
            try:
                sanitized, is_valid, risk_score = self._sensitive.scan("", sanitized)
                if not is_valid:
                    issues.append({
                        "scanner": "Sensitive",
                        "risk_score": risk_score,
                        "reason": "Sensitive content detected",
                    })
            except Exception as e:
                logger.warning(f"Sensitive scan error (skipping): {e}")

        if issues:
            logger.security_event(
                "output_sensitive_detected", risk_count=len(issues), issues=issues
            )
            return False, sanitized, issues

        return True, sanitized, []

    def scan_both(
        self, input_text: str, output_text: str
    ) -> Tuple[bool, bool, List[Dict[str, Any]]]:
        """Scan both input and output.

        Returns:
            (input_safe, output_safe, all_issues)
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