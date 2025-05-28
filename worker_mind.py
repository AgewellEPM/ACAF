# worker_mind.py
# The core Worker Mind orchestrator.
# Manages daily cycles, reflection, planning, and task execution.

import json
import time
import os
from datetime import datetime

# Assuming all other modules are in the same directory
from memory_manager import MemoryManager
from obedience_logic import ObedienceLogic
from autonomous_planner import AutonomousPlanner
from task_engine import TaskEngine
from tools import get_available_tools # We'll need this to inform planning/reflection

class WorkerMind:
    def __init__(self, memory_manager: MemoryManager, obedience_logic: ObedienceLogic,
                 autonomous_planner: AutonomousPlanner, task_engine: TaskEngine):
        self.memory_manager = memory_manager
        self.obedience_logic = obedience_logic
        self.autonomous_planner = autonomous_planner
        self.task_engine = task_engine
        self.manual_orders = None # Stores manual orders received from GUI
        self.current_plan = None
        self.current_goals = []
        self.daily_log = [] # Temporary log for the current day's activities

        # Load initial state if available (e.g., last plan, last orders)
        self._load_last_state()

    def _load_last_state(self):
        # Load last proposal
        try:
            if os.path.exists('last_proposal.json'):
                with open('last_proposal.json', 'r') as f:
                    data = json.load(f)
                    self.current_plan = data.get('plan')
                    self.current_goals = data.get('goals', [])
                    print(f"Loaded last plan: {self.current_plan}")
        except Exception as e:
            print(f"Error loading last_proposal.json: {e}")

        # Load last orders
        try:
            if os.path.exists('last_orders.json'):
                with open('last_orders.json', 'r') as f:
                    data = json.load(f)
                    self.manual_orders = data.get('orders')
                    print(f"Loaded last manual orders: {self.manual_orders}")
        except Exception as e:
            print(f"Error loading last_orders.json: {e}")


    def receive_manual_orders(self, orders: str):
        """Receives manual orders from the user (e.g., via GUI)."""
        print(f"Worker Mind received manual orders: {orders}")
        self.manual_orders = orders
        # Immediately save orders for persistence
        try:
            with open('last_orders.json', 'w') as f:
                json.dump({'orders': orders, 'timestamp': time.time()}, f, indent=4)
        except Exception as e:
            print(f"Error saving last_orders.json: {e}")

    def run_cycle(self):
        """Executes one full operational cycle of the Worker Mind."""
        print(f"--- Worker Mind Cycle initiated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        self.daily_log = [] # Reset daily log for this cycle

        # 1. Check for Manual Orders
        if self.manual_orders:
            print("Processing manual orders...")
            self._process_manual_orders()
            self.manual_orders = None # Clear orders after processing
        else:
            print("No manual orders. Proceeding with autonomous operation.")

        # 2. Reflection Phase
        print("Initiating reflection phase...")
        self._reflect_on_past_performance()

        # 3. Planning Phase
        print("Initiating planning phase...")
        self._plan_next_actions()

        # 4. Execution Phase
        print("Initiating execution phase...")
        self._execute_plan()

        # 5. Update Obedience and Joy
        print("Updating obedience and joy levels...")
        self.obedience_logic.update_levels()
        print(f"Current Joy: {self.obedience_logic.joy_level:.2f}, Obedience: {self.obedience_logic.obedience_level:.2f}")

        # 6. Log daily activities
        self.memory_manager.log_daily_activity(self.daily_log)
        print("Cycle completed. Daily activities logged.")

    def _process_manual_orders(self):
        """Processes manual orders, potentially overriding or influencing planning."""
        orders_to_process = self.manual_orders
        self.daily_log.append(f"Received manual orders: {orders_to_process}")
        print(f"Attempting to fulfill manual orders: '{orders_to_process}'")

        # For simplicity, manual orders directly become the current plan/goal
        # In a real system, an LLM would interpret and refine these orders into a plan
        self.current_plan = f"Fulfill manual order: {orders_to_process}"
        self.current_goals = [{"description": orders_to_process, "status": "pending"}]
        print(f"Manual orders converted to plan: {self.current_plan}")

        # Save the immediate plan based on manual orders
        try:
            with open('last_proposal.json', 'w') as f:
                json.dump({'plan': self.current_plan, 'goals': self.current_goals, 'source': 'manual_orders', 'timestamp': time.time()}, f, indent=4)
        except Exception as e:
            print(f"Error saving last_proposal.json after manual orders: {e}")


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
        print(f"Reflection: {reflection_result}")


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
            print(f"New Plan: {self.current_plan}")
            print(f"New Goals: {self.current_goals}")

            # Save the new proposal for persistence and GUI display
            try:
                with open('last_proposal.json', 'w') as f:
                    json.dump({'plan': self.current_plan, 'goals': self.current_goals, 'timestamp': time.time()}, f, indent=4)
            except Exception as e:
                print(f"Error saving last_proposal.json: {e}")
        else:
            print("Autonomous Planner could not propose a new plan. Sticking to previous or idle.")
            self.current_plan = "Idle or previous plan"
            self.current_goals = []
            self.daily_log.append("Autonomous Planner failed to propose a new plan.")


    def _execute_plan(self):
        """Executes the current plan using the task engine."""
        if not self.current_plan or not self.current_goals:
            print("No plan or goals to execute. Worker Mind is idle.")
            self.daily_log.append("No plan or goals to execute.")
            return

        print(f"Executing plan: '{self.current_plan}' with goals: {self.current_goals}")
        self.daily_log.append(f"Executing plan: '{self.current_plan}'")

        # The task engine will break down the plan/goals into actionable steps
        # and use tools. It will also update tool performance data.
        for goal in self.current_goals:
            if goal.get("status") == "pending":
                print(f"Attempting to achieve goal: {goal['description']}")
                self.daily_log.append(f"Attempting goal: {goal['description']}")
                success, output = self.task_engine.execute_task(goal['description'])

                if success:
                    goal["status"] = "achieved"
                    self.obedience_logic.adjust_joy(0.1) # Positive reinforcement
                    print(f"Goal '{goal['description']}' achieved. Output: {output}")
                    self.daily_log.append(f"Goal '{goal['description']}' achieved. Output: {output}")
                else:
                    goal["status"] = "failed"
                    self.obedience_logic.adjust_joy(-0.05) # Negative consequence
                    print(f"Goal '{goal['description']}' failed. Output: {output}")
                    self.daily_log.append(f"Goal '{goal['description']}' failed. Output: {output}")

        # After execution, update the plan/goals in the last_proposal.json
        try:
            with open('last_proposal.json', 'w') as f:
                json.dump({'plan': self.current_plan, 'goals': self.current_goals, 'timestamp': time.time()}, f, indent=4)
        except Exception as e:
            print(f"Error saving last_proposal.json after execution: {e}")

