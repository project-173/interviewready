from __future__ import annotations

import copy
import time
import uuid
from dataclasses import dataclass
from threading import RLock
from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

class ChatState(TypedDict):
    messages: Annotated[list, lambda x, y: x + y]
    user_id: str
    session_id: str


@dataclass(frozen=True)
class CheckpointRecord:
    checkpoint_id: str
    created_at: float
    state: object


class CheckpointStore:
    """Simple in-memory checkpoint store for demo-grade time travel."""

    def __init__(self) -> None:
        self._store: dict[str, list[CheckpointRecord]] = {}
        self._lock = RLock()

    def save(self, session_id: str, state: object) -> str:
        checkpoint_id = f"{session_id}-{uuid.uuid4().hex[:8]}-{int(time.time() * 1000)}"
        record = CheckpointRecord(
            checkpoint_id=checkpoint_id,
            created_at=time.time(),
            state=copy.deepcopy(state),
        )
        with self._lock:
            self._store.setdefault(session_id, []).append(record)
        return checkpoint_id

    def latest(self, session_id: str) -> Optional[CheckpointRecord]:
        with self._lock:
            records = self._store.get(session_id, [])
            return records[-1] if records else None

    def get(self, session_id: str, checkpoint_id: str) -> Optional[CheckpointRecord]:
        with self._lock:
            for record in self._store.get(session_id, []):
                if record.checkpoint_id == checkpoint_id:
                    return record
        return None

    def rewind(self, session_id: str, checkpoint_id: str) -> Optional[CheckpointRecord]:
        with self._lock:
            records = self._store.get(session_id, [])
            for index, record in enumerate(records):
                if record.checkpoint_id == checkpoint_id:
                    self._store[session_id] = records[: index + 1]
                    return record
        return None


_checkpoint_store = CheckpointStore()


def get_checkpoint_store() -> CheckpointStore:
    return _checkpoint_store

def create_chat_graph():
    workflow = StateGraph(ChatState)
    
    # We can add nodes here as needed, but for now, we'll use MemorySaver
    # to demonstrate persistent state management.
    
    return workflow.compile(checkpointer=MemorySaver())
