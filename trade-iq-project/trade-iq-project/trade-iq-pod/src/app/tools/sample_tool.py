"""Sample tool used by the orchestrator agent.

Replace the stub logic with real implementation.
"""

from langchain_core.tools import tool


@tool
def sample_tool(query: str) -> str:
    """Execute a sample operation and return a string result.

    Args:
        query: Input string to process.

    Returns:
        Processed result string.
    """
    # TODO: implement real tool logic
    return f"[sample_tool] processed: {query}"
