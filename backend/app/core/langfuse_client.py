"""Langfuse integration helper.

Provides a safe wrapper for Langfuse tracing so code can call
`langfuse.trace(...)` without requiring Langfuse to be installed or configured.

If Langfuse is available and API keys are set, this will create a real
Langfuse client. Otherwise it exposes a no-op implementation.

Usage:
    from app.core.langfuse_client import langfuse

    with langfuse.trace(name="my_trace", session_id="...") as trace:
        with trace.span(name="my_span"):
            ...
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Optional

from app.core.config import settings


class _NoopSpan:
    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, *_) -> None:
        return False

    def start_as_current_span(self, *args: Any, **kwargs: Any) -> "_NoopSpan":
        return self

    def update(self, *args: Any, **kwargs: Any) -> None:
        return None

    def set_output(self, *args: Any, **kwargs: Any) -> None:
        # Legacy alias used in parts of the codebase.
        return None

    def set_usage(self, *args: Any, **kwargs: Any) -> None:
        return None

    def score(self, *args: Any, **kwargs: Any) -> None:
        return None


class _SpanWrapper:
    """Wrap a real LangfuseSpan to provide a stable, minimal public API.

    The Langfuse Python client uses `start_as_current_span()` which returns a
    context manager yielding a `LangfuseSpan`. That span exposes `update()` and
    `score()`, but not the legacy `set_output()` helper used in our code.

    This wrapper provides `set_output()` and `update()` methods and delegates
    all other attribute access to the underlying span.
    """

    def __init__(self, span: Any):
        self._span = span

    def update(self, *args: Any, **kwargs: Any) -> Any:
        return self._span.update(*args, **kwargs)

    def set_output(self, output: Any, **kwargs: Any) -> Any:
        # Keep backwards compatibility with older code paths.
        return self._span.update(output=output, **kwargs)

    def score(self, *args: Any, **kwargs: Any) -> Any:
        return self._span.score(*args, **kwargs)

    def end(self, *args: Any, **kwargs: Any) -> Any:
        return getattr(self._span, "end", lambda *a, **k: None)(*args, **kwargs)

    def span(self, *args: Any, **kwargs: Any) -> Any:
        """Create a nested span within the current trace/span."""

        @contextmanager
        def _nested_span():
            with self._span.start_as_current_span(*args, **kwargs) as nested:
                yield _SpanWrapper(nested)

        return _nested_span()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._span, name)


class _LangfuseWrapper:
    def __init__(self, client: Any):
        self._client = client

    @contextmanager
    def trace(
        self,
        *,
        name: str,
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        input: Optional[Any] = None,
        output: Optional[Any] = None,
        version: Optional[str] = None,
        level: Optional[str] = None,
        status_message: Optional[str] = None,
        end_on_exit: Optional[bool] = None,
        **extra_metadata: Any,
    ):
        """Create a tracing span that can be used as a context manager.

        This is a thin wrapper over langfuse.Langfuse.start_as_current_span(),
        providing a stable API that supports a `session_id` argument and
        automatically merges extra keyword args into the `metadata` map.
        """

        merged_metadata = dict(metadata or {})
        if session_id is not None:
            merged_metadata["session_id"] = session_id

        # Include deployment environment automatically so traces can be filtered
        # based on whether the code is running locally vs deployed.
        if "environment" not in merged_metadata:
            merged_metadata["environment"] = settings.APP_ENV

        merged_metadata.update(extra_metadata)

        with self._client.start_as_current_span(
            name=name,
            metadata=merged_metadata,
            input=input,
            output=output,
            version=version,
            level=level,
            status_message=status_message,
            end_on_exit=end_on_exit,
        ) as span:
            yield _SpanWrapper(span)


def trace_agent_process(func):
    """Decorator to wrap agent.process() in a Langfuse trace span."""

    def wrapper(self, input_text, context, *args, **kwargs):
        from app.core.langfuse_client import langfuse

        session_id = getattr(context, "session_id", "unknown")
        agent_name = getattr(self, "name", self.__class__.__name__)

        with langfuse.trace(
            name=f"{agent_name}_process",
            session_id=session_id,
            metadata={
                "agent": agent_name,
                "input_length": len(input_text) if isinstance(input_text, str) else None,
            },
        ) as trace:
            try:
                response = func(self, input_text, context, *args, **kwargs)
                trace.update(output={
                    "response_length": len(str(getattr(response, "content", "")))
                })
                return response
            except Exception as e:
                trace.update(output={"error": str(e)})
                raise

    return wrapper


try:
    from langfuse import Langfuse  # type: ignore
except ImportError:  # pragma: no cover
    Langfuse = None  # type: ignore


if Langfuse and settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
    try:
        _client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
            environment=settings.APP_ENV,
            release=settings.VERSION,
        )
        langfuse = _LangfuseWrapper(_client)
    except Exception:
        langfuse = _NoopLangfuse()
else:
    langfuse = _NoopLangfuse()
