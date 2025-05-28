# tests/test_memory.py
# Unit tests for the memory module (AgentMemoryManager).

import pytest
import os
import json
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# Adjust path to import modules from src/
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from memory.AgentMemoryManager import MemoryManager
from config import AppConfig # For file paths

# Mocking external dependencies like OpenAI API calls
@pytest.fixture(autouse=True)
def mock_llm_client():
    """Mocks the OpenAI client for reflection LLM calls."""
    with patch('openai.OpenAI') as mock_openai:
        mock_instance = mock_openai.return_value
        mock_instance.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content='Mocked reflection insight.'))]
        )
        yield mock_instance

@pytest.fixture
def memory_manager_fixture():
    # Use temporary files for testing to avoid polluting real data
    temp_memory_file = "test_memory_manager_memory.json"
    temp_tool_perf_file = "test_memory_manager_tool_performance.json"
    if os.path.exists(temp_memory_file): os.remove(temp_memory_file)
    if os.path.exists(temp_tool_perf_file): os.remove(temp_tool_perf_file)

    mm = MemoryManager(memory_file=temp_memory_file, tool_performance_file=temp_tool_perf_file)
    yield mm
    if os.path.exists(temp_memory_file): os.remove(temp_memory_file)
    if os.path.exists(temp_tool_perf_file): os.remove(temp_tool_perf_file)

# --- Tests for AgentMemoryManager ---

def test_memory_manager_initialization(memory_manager_fixture):
    assert memory_manager_fixture.memory == {"daily_logs": [], "reflections": []}
    assert memory_manager_fixture.tool_performance_data == {"tool_usage": {}, "tool_success": {}}

def test_memory_manager_load_existing_memory(memory_manager_fixture):
    # Manually create a dummy memory file
    dummy_memory = {"daily_logs": [{"date": "2023-01-01", "activities": ["activity 1"]}], "reflections": []}
    with open(memory_manager_fixture.memory_file, 'w') as f:
        json.dump(dummy_memory, f)

    # Re-initialize MemoryManager to load the dummy data
    mm = MemoryManager(memory_file=memory_manager_fixture.memory_file, tool_performance_file=memory_manager_fixture.tool_performance_file)
    assert mm.memory == dummy_memory

def test_memory_manager_log_daily_activity(memory_manager_fixture):
    activities = ["Task A completed", "Tool X used"]
    memory_manager_fixture.log_daily_activity(activities)

    assert len(memory_manager_fixture.memory["daily_logs"]) == 1
    log_entry = memory_manager_fixture.memory["daily_logs"][0]
    assert log_entry["activities"] == activities
    assert "date" in log_entry
    assert "timestamp" in log_entry

    # Verify it's saved to file
    with open(memory_manager_fixture.memory_file, 'r') as f:
        saved_memory = json.load(f)
        assert len(saved_memory["daily_logs"]) == 1

def test_memory_manager_get_recent_activities(memory_manager_fixture):
    # Add activities for different dates
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)
    eight_days_ago = today - timedelta(days=8)

    memory_manager_fixture.memory["daily_logs"].append({
        "date": eight_days_ago.strftime("%Y-%m-%d"),
        "activities": ["old activity"],
        "timestamp": eight_days_ago.isoformat()
    })
    memory_manager_fixture.memory["daily_logs"].append({
        "date": two_days_ago.strftime("%Y-%m-%d"),
        "activities": ["recent activity 1"],
        "timestamp": two_days_ago.isoformat()
    })
    memory_manager_fixture.memory["daily_logs"].append({
        "date": yesterday.strftime("%Y-%m-%d"),
        "activities": ["recent activity 2"],
        "timestamp": yesterday.isoformat()
    })
    memory_manager_fixture.memory["daily_logs"].append({
        "date": today.strftime("%Y-%m-%d"),
        "activities": ["today's activity"],
        "timestamp": today.isoformat()
    })
    memory_manager_fixture._save_memory() # Save to ensure it's loaded if re-init'd

    recent = memory_manager_fixture.get_recent_activities(days=3) # Should get activities from today, yesterday, 2 days ago
    assert len(recent) == 3
    assert "today's activity" in recent[2]["activities"]
    assert "recent activity 2" in recent[1]["activities"]
    assert "recent activity 1" in recent[0]["activities"]
    assert not any("old activity" in a["activities"] for a in recent)

def test_memory_manager_record_tool_performance(memory_manager_fixture):
    memory_manager_fixture.record_tool_performance("search_web", True)
    memory_manager_fixture.record_tool_performance("search_web", True)
    memory_manager_fixture.record_tool_performance("write_file", False)

    perf_data = memory_manager_fixture.get_tool_performance_data()
    assert perf_data["tool_usage"]["search_web"] == 2
    assert perf_data["tool_success"]["search_web"] == 2
    assert perf_data["tool_usage"]["write_file"] == 1
    assert perf_data["tool_success"]["write_file"] == 0

    # Verify it's saved to file
    with open(memory_manager_fixture.tool_performance_file, 'r') as f:
        saved_perf = json.load(f)
        assert saved_perf["tool_usage"]["search_web"] == 2

def test_memory_manager_reflect_with_llm(memory_manager_fixture, mock_llm_client):
    reflection_prompt = "Reflect on this."
    reflection_result = memory_manager_fixture.reflect(reflection_prompt)

    assert reflection_result == "Mocked reflection insight."
    mock_llm_client.chat.completions.create.assert_called_once()
    # Verify reflection is saved
    assert len(memory_manager_fixture.memory["reflections"]) == 1
    assert memory_manager_fixture.memory["reflections"][0]["reflection"] == "Mocked reflection insight."

def test_memory_manager_reflect_no_llm(memory_manager_fixture):
    memory_manager_fixture.llm_client = None # Simulate no LLM client
    reflection_prompt = "Reflect on this."
    reflection_result = memory_manager_fixture.reflect(reflection_prompt)

    assert "No LLM available to analyze performance." in reflection_result
    assert len(memory_manager_fixture.memory["reflections"]) == 0 # No reflection saved if LLM not available
