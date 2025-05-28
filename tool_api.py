# tool_api.py
# Provides a consistent interface for calling tools.
# This module acts as a wrapper around the actual tool functions.

from typing import Any, Dict
from tools import get_tool_by_name

def call_tool(tool_name: str, **kwargs) -> Any:
    """
    Calls a specified tool with the given arguments.

    Args:
        tool_name (str): The name of the tool to call.
        **kwargs: Arbitrary keyword arguments to pass to the tool's function.

    Returns:
        Any: The result returned by the tool's function.

    Raises:
        ValueError: If the tool is not found or arguments are invalid.
    """
    tool = get_tool_by_name(tool_name)
    if not tool:
        raise ValueError(f"Tool '{tool_name}' not found.")

    # Basic argument validation (can be expanded with a full schema validator)
    for arg_name, arg_schema in tool.args_schema.items():
        if arg_name not in kwargs:
            # For simplicity, assuming all args in schema are required for now
            # In a real system, you'd check for 'required' in schema
            raise ValueError(f"Missing required argument '{arg_name}' for tool '{tool_name}'.")

    # Call the tool's function with the provided arguments
    try:
        print(f"ToolAPI: Calling tool '{tool_name}' with args: {kwargs}")
        result = tool.func(**kwargs)
        print(f"ToolAPI: Tool '{tool_name}' returned: {result[:100]}...") # Log first 100 chars
        return result
    except TypeError as e:
        raise ValueError(f"Invalid arguments for tool '{tool_name}': {e}. Args provided: {kwargs}")
    except Exception as e:
        raise Exception(f"An error occurred during tool '{tool_name}' execution: {e}")

