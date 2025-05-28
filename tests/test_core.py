# tests/test_core.py
# Unit and integration tests for the core Worker Mind components.

import pytest
import os
import json
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# Adjust path to import modules from src/
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from core.WorkerMindOrchestrator import WorkerMind
from core.ObedienceModule import ObedienceLogic
from core.AutonomousPlanner import AutonomousPlanner
from agents.TaskExecutionEngine import TaskEngine
from memory.AgentMemoryManager import MemoryManager
from knowledge_base.LocalKnowledgeBaseManager import KnowledgeBaseManager
from config import AppConfig

# Mocking external dependencies like OpenAI API calls
@pytest.fixture(autouse=True)
def mock_llm_client():
    """Mocks the OpenAI client for all LLM calls."""
    with patch('openai.OpenAI') as mock_openai:
        mock_instance = mock_openai.return_value
        mock_instance.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content='{"plan": "Test Plan", "goals": [{"description": "Test Goal", "status": "pending"}]}'
                                              if 'plan' in Mock.call_args.args[0] else
                                              '{"direct_response": "true", "response_content": "Task completed directly."}'
                                              if 'direct_response' in Mock.call_args.args[0] else
                                              '{"tool_name": "search_web", "tool_args": {"query": "test"}}'
                                              if 'tool_name' in Mock.call_args.args[0] else
                                              'N/A'
                                             ))]
        )
        yield mock_instance

# Fixtures for component instances
@pytest.fixture
def memory_manager_fixture():
    # Use temporary files for testing to avoid polluting real data
    temp_memory_file = "test_worker_mind_memory.json"
    temp_tool_perf_file = "test_tool_performance_data.json"
    if os.path.exists(temp_memory_file): os.remove(temp_memory_file)
    if os.path.exists(temp_tool_perf_file): os.remove(temp_tool_perf_file)

    mm = MemoryManager(memory_file=temp_memory_file, tool_performance_file=temp_tool_perf_file)
    yield mm
    if os.path.exists(temp_memory_file): os.remove(temp_memory_file)
    if os.path.exists(temp_tool_perf_file): os.remove(temp_tool_perf_file)

@pytest.fixture
def obedience_logic_fixture():
    temp_state_file = "test_worker_mind_state.json"
    if os.path.exists(temp_state_file): os.remove(temp_state_file)
    ol = ObedienceLogic(state_file=temp_state_file)
    yield ol
    if os.path.exists(temp_state_file): os.remove(temp_state_file)

@pytest.fixture
def knowledge_base_manager_fixture():
    temp_kb_file = "test_aac_theory_pack.json"
    if os.path.exists(temp_kb_file): os.remove(temp_kb_file)
    kbm = KnowledgeBaseManager(kb_file=temp_kb_file)
    yield kbm
    if os.path.exists(temp_kb_file): os.remove(temp_kb_file)

@pytest.fixture
def task_engine_fixture(memory_manager_fixture, knowledge_base_manager_fixture):
    te = TaskEngine(memory_manager_fixture, knowledge_base_manager_fixture)
    yield te

@pytest.fixture
def autonomous_planner_fixture(memory_manager_fixture):
    ap = AutonomousPlanner(memory_manager_fixture)
    yield ap

@pytest.fixture
def worker_mind_fixture(memory_manager_fixture, obedience_logic_fixture, autonomous_planner_fixture, task_engine_fixture):
    temp_last_proposal = "test_last_proposal.json"
    temp_last_orders = "test_last_orders.json"
    if os.path.exists(temp_last_proposal): os.remove(temp_last_proposal)
    if os.path.exists(temp_last_orders): os.remove(temp_last_orders)

    # Patch file paths in AppConfig for testing
    with patch.object(AppConfig, 'LAST_PROPOSAL_FILE', temp_last_proposal), \
         patch.object(AppConfig, 'LAST_ORDERS_FILE', temp_last_orders):
        wm = WorkerMind(memory_manager_fixture, obedience_logic_fixture, autonomous_planner_fixture, task_engine_fixture)
        yield wm

    if os.path.exists(temp_last_proposal): os.remove(temp_last_proposal)
    if os.path.exists(temp_last_orders): os.remove(temp_last_orders)


# --- Tests for WorkerMindOrchestrator ---

def test_worker_mind_initialization(worker_mind_fixture):
    assert worker_mind_fixture.current_plan is None
    assert worker_mind_fixture.current_goals == []
    assert worker_mind_fixture.manual_orders is None

def test_worker_mind_receive_manual_orders(worker_mind_fixture):
    orders = "Perform a quick web search for 'AI news'."
    worker_mind_fixture.receive_manual_orders(orders)
    assert worker_mind_fixture.manual_orders == orders
    # Check if orders are saved to file
    with open("test_last_orders.json", 'r') as f:
        data = json.load(f)
        assert data['orders'] == orders

@patch('time.sleep', return_value=None) # Mock time.sleep to speed up tests
def test_worker_mind_run_cycle_manual_orders(mock_sleep, worker_mind_fixture, mock_llm_client):
    orders = "Test manual order execution."
    worker_mind_fixture.receive_manual_orders(orders)

    # Ensure LLM returns a valid plan for manual orders
    mock_llm_client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content='{"plan": "Fulfill manual order: Test manual order execution.", "goals": [{"description": "Test manual order execution.", "status": "pending"}]}'
                                     ))]
    )

    worker_mind_fixture.run_cycle()

    assert worker_mind_fixture.manual_orders is None # Orders should be consumed
    assert "Fulfill manual order" in worker_mind_fixture.current_plan
    assert len(worker_mind_fixture.current_goals) == 1
    assert worker_mind_fixture.current_goals[0]['status'] == 'achieved' # Assuming task engine succeeds

    # Verify reflection was called
    mock_llm_client.chat.completions.create.assert_called()
    assert any("reflection" in call.args[0] for call in mock_llm_client.chat.completions.create.call_args_list)

    # Verify planning was called
    assert any("plan" in call.args[0] for call in mock_llm_client.chat.completions.create.call_args_list)

    # Verify daily log was updated
    memory_dump = worker_mind_fixture.memory_manager.get_full_memory_dump()
    assert len(memory_dump['daily_logs']) > 0
    assert any("Received manual orders" in activity for activity in memory_dump['daily_logs'][-1]['activities'])

@patch('time.sleep', return_value=None)
def test_worker_mind_run_cycle_autonomous(mock_sleep, worker_mind_fixture, mock_llm_client):
    # Reset manual orders for autonomous test
    worker_mind_fixture.manual_orders = None
    if os.path.exists("test_last_orders.json"): os.remove("test_last_orders.json")

    # Ensure LLM returns a valid plan for autonomous operation
    mock_llm_client.chat.completions.create.side_effect = [
        Mock(choices=[Mock(message=Mock(content='{"reflection": "Good job overall."}'))]), # For reflection
        Mock(choices=[Mock(message=Mock(content='{"plan": "Autonomous Plan", "goals": [{"description": "Autonomous Goal", "status": "pending"}]}')), # For planning
        Mock(choices=[Mock(message=Mock(content='{"direct_response": "true", "response_content": "Autonomous task completed."}')), # For task execution
    ]

    worker_mind_fixture.run_cycle()

    assert worker_mind_fixture.manual_orders is None
    assert "Autonomous Plan" in worker_mind_fixture.current_plan
    assert len(worker_mind_fixture.current_goals) == 1
    assert worker_mind_fixture.current_goals[0]['status'] == 'achieved'

    # Verify reflection and planning were called
    assert mock_llm_client.chat.completions.create.call_count >= 2

    memory_dump = worker_mind_fixture.memory_manager.get_full_memory_dump()
    assert len(memory_dump['daily_logs']) > 0
    assert any("Executing plan: 'Autonomous Plan'" in activity for activity in memory_dump['daily_logs'][-1]['activities'])

# --- Tests for ObedienceModule ---

def test_obedience_logic_initial_levels(obedience_logic_fixture):
    assert obedience_logic_fixture.joy_level == 0.5
    assert obedience_logic_fixture.obedience_level == 0.5

def test_obedience_logic_adjust_joy(obedience_logic_fixture):
    obedience_logic_fixture.adjust_joy(0.2)
    assert obedience_logic_fixture.joy_level == 0.7
    obedience_logic_fixture.adjust_joy(-0.8)
    assert obedience_logic_fixture.joy_level == 0.0 # Clamped

def test_obedience_logic_adjust_obedience(obedience_logic_fixture):
    obedience_logic_fixture.adjust_obedience(0.3)
    assert obedience_logic_fixture.obedience_level == 0.8
    obedience_logic_fixture.adjust_obedience(-0.9)
    assert obedience_logic_fixture.obedience_level == 0.0 # Clamped

@patch('datetime.datetime')
def test_obedience_logic_update_levels_decay(mock_datetime, obedience_logic_fixture):
    # Set initial time
    mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
    mock_datetime.fromisoformat.side_effect = lambda x: datetime.fromisoformat(x) # Allow real parsing

    # First save to set last_update_time
    obedience_logic_fixture._save_state()

    # Advance time by 10 seconds
    mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 10)
    obedience_logic_fixture.update_levels()

    expected_joy_decay = AppConfig.JOY_DECAY_RATE_PER_SEC * 10
    expected_obedience_decay = AppConfig.OBEDIENCE_DECAY_RATE_PER_SEC * 10

    # Check if levels decreased (approximately, due to float precision)
    assert obedience_logic_fixture.joy_level < 0.5
    assert obedience_logic_fixture.obedience_level < 0.5
    assert obedience_logic_fixture.joy_level == pytest.approx(0.5 - expected_joy_decay, abs=1e-5)
    assert obedience_logic_fixture.obedience_level == pytest.approx(0.5 - expected_obedience_decay, abs=1e-5)

# --- Tests for AutonomousPlanner ---

def test_autonomous_planner_propose_plan_and_goals_success(autonomous_planner_fixture, mock_llm_client):
    mock_llm_client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content='{"plan": "Develop new feature", "goals": [{"description": "Implement sub-task A", "status": "pending"}]}'
                                     ))]
    )
    plan, goals = autonomous_planner_fixture.propose_plan_and_goals("Some context")
    assert plan == "Develop new feature"
    assert len(goals) == 1
    assert goals[0]["description"] == "Implement sub-task A"

def test_autonomous_planner_propose_plan_and_goals_invalid_json(autonomous_planner_fixture, mock_llm_client):
    mock_llm_client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content='This is not JSON.'))]
    )
    plan, goals = autonomous_planner_fixture.propose_plan_and_goals("Some context")
    assert "Failed to generate a valid plan" in plan
    assert goals == []

def test_autonomous_planner_no_llm_client(autonomous_planner_fixture):
    autonomous_planner_fixture.llm_client = None # Simulate no LLM client
    plan, goals = autonomous_planner_fixture.propose_plan_and_goals("Some context")
    assert "No LLM available for planning." in plan
    assert goals == []
