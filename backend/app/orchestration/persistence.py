from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

class ChatState(TypedDict):
    messages: Annotated[list, lambda x, y: x + y]
    user_id: str
    session_id: str

def create_chat_graph():
    workflow = StateGraph(ChatState)
    
    # We can add nodes here as needed, but for now, we'll use MemorySaver
    # to demonstrate persistent state management.
    
    return workflow.compile(checkpointer=MemorySaver())
