"""Agent state definition for LangGraph."""
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State schema for the network diagnosis agent.
    
    Attributes:
        messages: List of conversation messages (human, AI, tool calls/results).
                  Uses add_messages reducer to append new messages.
    """
    messages: Annotated[list, add_messages]
