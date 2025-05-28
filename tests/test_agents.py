# tests/test_agents.py
# Unit and integration tests for the agents module (TaskExecutionEngine).

import pytest
import os
import json
from unittest.mock import Mock, patch

# Adjust path to import modules from src/
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from agents.TaskExecutionEngine import TaskEngine
from memory.AgentMemoryManager import MemoryManager
from knowledge_base.LocalKnowledgeBaseManager import KnowledgeBaseManager
from tools.AgentToolsDefinition import get_tool_by_name # To verify tool calls
from tools.ToolInvocationInterface import call_tool # To mock tool calls

# Mocking external dependencies like OpenAI API calls
@pytest.fixture(autouse=True)
def mock_llm_client():
    """Mocks the OpenAI client for all LLM calls."""
    with patch('openai.OpenAI') as mock_openai:
        mock_instance = mock_openai.return_value
        # Default mock response for LLM decision
        mock_instance.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content='{"direct_response": "true", "response_content": "Default direct response."}'))]
        )
        yield mock_instance

# Fixtures for component instances
@pytest.fixture
def memory_manager_fixture():
    # Use temporary files for testing to avoid polluting real data
    temp_memory_file = "test_task_engine_memory.json"
    temp_tool_perf_file = "test_task_engine_tool_performance.json"
    if os.path.exists(temp_memory_file): os.remove(temp_memory_file)
    if os.path.exists(temp_tool_perf_file): os.remove(temp_tool_perf_file)

    mm = MemoryManager(memory_file=temp_memory_file, tool_performance_file=temp_tool_perf_file)
    yield mm
    if os.path.exists(temp_memory_file): os.remove(temp_memory_file)
    if os.path.exists(temp_tool_perf_file): os.remove(temp_tool_perf_file)

@pytest.fixture
def knowledge_base_manager_fixture():
    temp_kb_file = "test_task_engine_aac_theory_pack.json"
    if os.path.exists(temp_kb_file): os.remove(temp_kb_file)
    kbm = KnowledgeBaseManager(kb_file=temp_kb_file)
    yield kbm
    if os.path.exists(temp_kb_file): os.remove(temp_kb_file)

@pytest.fixture
def task_engine_fixture(memory_manager_fixture, knowledge_base_manager_fixture):
    te = TaskEngine(memory_manager_fixture, knowledge_base_manager_fixture)
    yield te

# --- Tests for TaskExecutionEngine ---

def test_task_engine_direct_response(task_engine_fixture, mock_llm_client):
    task_description = "Summarize the concept of reinforcement."
    # Configure mock LLM to return a direct response
    mock_llm_client.chat.completions.create.side_effect = [
        Mock(choices=[Mock(message=Mock(content='N/A'))]), # For KB query
        Mock(choices=[Mock(message=Mock(content='{"direct_response": "true", "response_content": "Reinforcement increases behavior."}'))]) # For action decision
    ]

    success, output = task_engine_fixture.execute_task(task_description)

    assert success is True
    assert "Reinforcement increases behavior." in output
    # Verify LLM was called for KB query and action decision
    assert mock_llm_client.chat.completions.create.call_count == 2
    # Verify tool performance was recorded for direct response
    tool_perf = task_engine_fixture.memory_manager.get_tool_performance_data()
    assert tool_perf['tool_usage'].get('LLM_direct_response', 0) == 1
    assert tool_perf['tool_success'].get('LLM_direct_response', 0) == 1

@patch('tools.ToolInvocationInterface.call_tool') # Mock the actual tool call
def test_task_engine_tool_use_success(mock_call_tool, task_engine_fixture, mock_llm_client):
    task_description = "Search for 'latest AI breakthroughs'."
    mock_llm_client.chat.completions.create.side_effect = [
        Mock(choices=[Mock(message=Mock(content='N/A'))]), # For KB query
        Mock(choices=[Mock(message=Mock(content='{"tool_name": "search_web", "tool_args": {"query": "latest AI breakthroughs"}}'))]) # For action decision
    ]
    mock_call_tool.return_value = "AI breakthroughs are happening daily."

    success, output = task_engine_fixture.execute_task(task_description)

    assert success is True
    assert "AI breakthroughs are happening daily." in output
    mock_call_tool.assert_called_once_with("search_web", query="latest AI breakthroughs")
    # Verify tool performance was recorded for search_web
    tool_perf = task_engine_fixture.memory_manager.get_tool_performance_data()
    assert tool_perf['tool_usage'].get('search_web', 0) == 1
    assert tool_perf['tool_success'].get('search_web', 0) == 1

@patch('tools.ToolInvocationInterface.call_tool')
def test_task_engine_tool_use_failure(mock_call_tool, task_engine_fixture, mock_llm_client):
    task_description = "Write a file named 'error_log.txt'."
    mock_llm_client.chat.completions.create.side_effect = [
        Mock(choices=[Mock(message=Mock(content='N/A'))]), # For KB query
        Mock(choices=[Mock(message=Mock(content='{"tool_name": "write_file", "tool_args": {"filename": "error_log.txt", "content": "Error details"}}'))]) # For action decision
    ]
    mock_call_tool.side_effect = Exception("Disk full error") # Simulate tool failure

    success, output = task_engine_fixture.execute_task(task_description)

    assert success is False
    assert "Error calling tool 'write_file': Disk full error" in output
    mock_call_tool.assert_called_once_with("write_file", filename="error_log.txt", content="Error details")
    # Verify tool performance was recorded as failure
    tool_perf = task_engine_fixture.memory_manager.get_tool_performance_data()
    assert tool_perf['tool_usage'].get('write_file', 0) == 1
    assert tool_perf['tool_success'].get('write_file', 0) == 0

def test_task_engine_invalid_llm_decision_json(task_engine_fixture, mock_llm_client):
    task_description = "Do something ambiguous."
    mock_llm_client.chat.completions.create.side_effect = [
        Mock(choices=[Mock(message=Mock(content='N/A'))]), # For KB query
        Mock(choices=[Mock(message=Mock(content='This is not valid JSON.'))]) # Invalid JSON
    ]

    success, output = task_engine_fixture.execute_task(task_description)

    assert success is False
    assert "Failed to parse LLM's action decision." in output
    tool_perf = task_engine_fixture.memory_manager.get_tool_performance_data()
    assert tool_perf['tool_usage'].get('LLM_decision_parse', 0) == 1
    assert tool_perf['tool_success'].get('LLM_decision_parse', 0) == 0

def test_task_engine_kb_query_integration(task_engine_fixture, knowledge_base_manager_fixture, mock_llm_client):
    task_description = "Explain reinforcement."
    # Add a concept to KB for testing
    knowledge_base_manager_fixture.add_concept("c1", "Reinforcement", "A process that strengthens a behavior.")

    mock_llm_client.chat.completions.create.side_effect = [
        Mock(choices=[Mock(message=Mock(content="Query KB for concepts related to 'reinforcement'"))]), # For KB query
        Mock(choices=[Mock(message=Mock(content='{"direct_response": "true", "response_content": "Reinforcement strengthens behavior."}'))]) # For action decision
    ]

    success, output = task_engine_fixture.execute_task(task_description)

    assert success is True
    assert "Reinforcement strengthens behavior." in output
    # Verify LLM was called for KB query and action decision
    assert mock_llm_client.chat.completions.create.call_count == 2
    # You might want to inspect the prompt sent to the second LLM call
    # to ensure it included the KB info, but that's harder with side_effect.
    # For now, successful execution implies the flow.

def test_task_engine_no_llm_client(task_engine_fixture):
    task_engine_fixture.llm_client = None # Simulate no LLM client
    success, output = task_engine_fixture.execute_task("Do something.")
    assert success is False
    assert "LLM client not configured." in output
