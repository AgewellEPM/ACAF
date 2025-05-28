# src/core/WorkerMindOrchestrator.py
# The core Worker Mind orchestrator.
# Manages daily cycles, reflection, planning, and task execution.

import json
import time
import os
from datetime import datetime
import logging

# Adjust path to import modules from src/
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


# Assuming all other modules are in the same directory under src/
from memory.AgentMemoryManager import MemoryManager
from core.ObedienceModule import ObedienceLogic
from core.AutonomousPlanner import AutonomousPlanner
from agents.TaskExecutionEngine import TaskEngine
from tools.AgentToolsDefinition import get_available_tools # We'll need this to inform planning/reflection
from config import AppConfig # Import AppConfig for file paths and settings

logger = logging.getLogger(__name__)

class WorkerMind:
    def __init__(self, memory_manager: MemoryManager, obedience_logic: ObedienceLogic,
                 autonomous_planner: AutonomousPlanner, task_engine: TaskEngine,
                 last_proposal_file: str = AppConfig.LAST_PROPOSAL_FILE,
                 last_orders_file: str = AppConfig.LAST_ORDERS_FILE):
        self.memory_manager = memory_manager
        self.obedience_logic = obedience_logic
        self.autonomous_planner = autonomous_planner
        self.task_engine = task_engine
        self.manual_orders = None # Stores manual orders received from GUI
        self.current_plan = None
        self.current_goals = []
        self.daily_log = [] # Temporary log for the current day's activities

        # File paths for persistence, passed from GUI or defaulting to AppConfig
        self.last_proposal_file = last_proposal_file
        self.last_orders_file = last_orders_file


        # Load initial state if available (e.g., last plan, last orders)
        self._load_last_state()

    def _load_last_state(self):
        """Loads the last proposal and manual orders from respective files."""
        # Load last proposal
        try:
            if os.path.exists(self.last_proposal_file):
                with open(self.last_proposal_file, 'r') as f:
                    data = json.load(f)
                    self.current_plan = data.get('plan')
                    self.current_goals = data.get('goals', [])
                    logger.info(f"Loaded last plan: {self.current_plan}")
            else:
                logger.info(f"No existing proposal file found at {self.last_proposal_file}.")
        except Exception as e:
            logger.error(f"Error loading {self.last_proposal_file}: {e}")

        # Load last orders
        try:
            if os.path.exists(self.last_orders_file):
                with open(self.last_orders_file, 'r') as f:
                    data = json.load(f)
                    self.manual_orders = data.get('orders')
                    logger.info(f"Loaded last manual orders: {self.manual_orders}")
            else:
                logger.info(f"No existing orders file found at {self.last_orders_file}.")
        except Exception as e:
            logger.error(f"Error loading {self.last_orders_file}: {e}")


    def receive_manual_orders(self, orders: str):
        """Receives manual orders from the user (e.g., via GUI)."""
        logger.info(f"Worker Mind received manual orders: {orders}")
        self.manual_orders = orders
        # Immediately save orders for persistence
        try:
            with open(self.last_orders_file, 'w') as f:
                json.dump({'orders': orders, 'timestamp': time.time()}, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving {self.last_orders_file}: {e}")

    def run_cycle(self):
        """Executes one full operational cycle of the Worker Mind."""
        logger.info(f"--- Worker Mind Cycle initiated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        self.daily_log = [] # Reset daily log for this cycle

        # 1. Check for Manual Orders
        if self.manual_orders:
            logger.info("Processing manual orders...")
            self._process_manual_orders()
            self.manual_orders = None # Clear orders after processing
        else:
            logger.info("No manual orders. Proceeding with autonomous operation.")

        # 2. Reflection Phase
        logger.info("Initiating reflection phase...")
        self._reflect_on_past_performance()

        # 3. Planning Phase
        logger.info("Initiating planning phase...")
        self._plan_next_actions()

        # 4. Execution Phase
        logger.info("Initiating execution phase...")
        self._execute_plan()

        # 5. Update Obedience and Joy
        logger.info("Updating obedience and joy levels...")
        self.obedience_logic.update_levels()
        logger.info(f"Current Joy: {self.obedience_logic.joy_level:.2f}, Obedience: {self.obedience_logic.obedience_level:.2f}")

        # 6. Log daily activities
        self.memory_manager.log_daily_activity(self.daily_log)
        logger.info("Cycle completed. Daily activities logged.")

    def _process_manual_orders(self):
        """Processes manual orders, potentially overriding or influencing planning."""
        orders_to_process = self.manual_orders
        self.daily_log.append(f"Received manual orders: {orders_to_process}")
        logger.info(f"Attempting to fulfill manual orders: '{orders_to_process}'")

        # For simplicity, manual orders directly become the current plan/goal
        # In a real system, an LLM would interpret and refine these orders into a plan
        self.current_plan = f"Fulfill manual order: {orders_to_process}"
        self.current_goals = [{"description": orders_to_process, "status": "pending"}]
        logger.info(f"Manual orders converted to plan: {self.current_plan}")

        # Save the immediate plan based on manual orders
        try:
            with open(self.last_proposal_file, 'w') as f:
                json.dump({'plan': self.current_plan, 'goals': self.current_goals, 'source': 'manual_orders', 'timestamp': time.time()}, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving {self.last_proposal_file} after manual orders: {e}")


    def _reflect_on_past_performance(self):
        """Triggers the memory manager to perform reflection."""
        # Get recent activities and tool performance for reflection context
        recent_activities = self.memory_manager.get_recent_activities(days=1) # Last day's activities
        tool_performance = self.memory_manager.get_tool_performance_data()
        current_obedience_joy = {
            "joy_level": self.obedience_logic.joy_level,
            "obedience_level": self.obedience_logic.obedience_level
        }

        reflection_prompt = (
            "Based on the following recent activities, tool performance, and current internal states, "
            "reflect on what went well, what could be improved, and any emerging patterns or issues. "
            "Consider how actions impacted joy and obedience. "
            "Recent Activities:\n" + json.dumps(recent_activities, indent=2) +
            "\nTool Performance:\n" + json.dumps(tool_performance, indent=2) +
            "\nCurrent Internal States:\n" + json.dumps(current_obedience_joy, indent=2)
        )
        reflection_result = self.memory_manager.reflect(reflection_prompt)
        self.daily_log.append(f"Reflection completed: {reflection_result}")
        logger.info(f"Reflection: {reflection_result}")


    def _plan_next_actions(self):
        """Triggers the autonomous planner to propose goals and a plan."""
        # Provide context for planning
        current_state = {
            "last_plan": self.current_plan,
            "last_goals": self.current_goals,
            "joy_level": self.obedience_logic.joy_level,
            "obedience_level": self.obedience_logic.obedience_level,
            "available_tools": [tool.name for tool in get_available_tools()]
        }
        planning_prompt = (
            "Given the current internal states, past performance, and available tools, "
            "propose a set of strategic goals and a detailed plan to achieve them. "
            "Prioritize tasks that improve obedience and joy, and address any issues identified in reflection. "
            "Consider the following context:\n" + json.dumps(current_state, indent=2)
        )

        proposed_plan, proposed_goals = self.autonomous_planner.propose_plan_and_goals(planning_prompt)

        if proposed_plan and proposed_goals:
            self.current_plan = proposed_plan
            self.current_goals = proposed_goals
            self.daily_log.append(f"New plan proposed: {self.current_plan}")
            self.daily_log.append(f"New goals proposed: {self.current_goals}")
            logger.info(f"New Plan: {self.current_plan}")
            logger.info(f"New Goals: {self.current_goals}")

            # Save the new proposal for persistence and GUI display
            try:
                with open(self.last_proposal_file, 'w') as f:
                    json.dump({'plan': self.current_plan, 'goals': self.current_goals, 'timestamp': time.time()}, f, indent=4)
            except Exception as e:
                logger.error(f"Error saving {self.last_proposal_file}: {e}")
        else:
            logger.warning("Autonomous Planner could not propose a new plan. Sticking to previous or idle.")
            self.current_plan = "Idle or previous plan"
            self.current_goals = []
            self.daily_log.append("Autonomous Planner failed to propose a new plan.")


    def _execute_plan(self):
        """Executes the current plan using the task engine."""
        if not self.current_plan or not self.current_goals:
            logger.info("No plan or goals to execute. Worker Mind is idle.")
            self.daily_log.append("No plan or goals to execute.")
            return

        logger.info(f"Executing plan: '{self.current_plan}' with goals: {self.current_goals}")
        self.daily_log.append(f"Executing plan: '{self.current_plan}'")

        # The task engine will break down the plan/goals into actionable steps
        # and use tools. It will also update tool performance data.
        for goal in self.current_goals:
            if goal.get("status") == "pending":
                logger.info(f"Attempting to achieve goal: {goal['description']}")
                self.daily_log.append(f"Attempting goal: {goal['description']}")
                success, output = self.task_engine.execute_task(goal['description'])

                if success:
                    goal["status"] = "achieved"
                    self.obedience_logic.adjust_joy(AppConfig.JOY_BOOST_ON_SUCCESS) # Positive reinforcement (add this to AppConfig)
                    logger.info(f"Goal '{goal['description']}' achieved. Output: {output}")
                    self.daily_log.append(f"Goal '{goal['description']}' achieved. Output: {output}")
                else:
                    goal["status"] = "failed"
                    self.obedience_logic.adjust_joy(AppConfig.JOY_REDUCE_ON_FAILURE) # Negative consequence (add this to AppConfig)
                    logger.warning(f"Goal '{goal['description']}' failed. Output: {output}")
                    self.daily_log.append(f"Goal '{goal['description']}' failed. Output: {output}")

        # After execution, update the plan/goals in the last_proposal.json
        try:
            with open(self.last_proposal_file, 'w') as f:
                json.dump({'plan': self.current_plan, 'goals': self.current_goals, 'timestamp': time.time()}, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving {self.last_proposal_file} after execution: {e}")

