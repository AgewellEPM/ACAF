# autonomous_planner.py
# The brain for strategic planning and goal proposal.
# Uses an LLM to generate plans and goals based on current state and reflection.

import json
import os
from typing import Tuple, List, Dict, Any
from dotenv import load_dotenv
import openai # Using OpenAI for demonstration purposes

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("OPENAI_API_KEY not found in .env file. Planning will be limited.")

from memory_manager import MemoryManager # For accessing memory for context

class AutonomousPlanner:
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.llm_client = None # Placeholder for LLM client

        if OPENAI_API_KEY:
            try:
                self.llm_client = openai.OpenAI(api_key=OPENAI_API_KEY)
            except Exception as e:
                print(f"AutonomousPlanner: Failed to initialize OpenAI client: {e}")
                self.llm_client = None
        else:
            print("AutonomousPlanner: OpenAI client not initialized due to missing API key.")

    def _call_llm(self, prompt: str, model: str = "gpt-4o", temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Helper to call the LLM."""
        if not self.llm_client:
            print("LLM client not available. Cannot make LLM call for planning.")
            return "Error: LLM client not configured."
        try:
            response = self.llm_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a strategic planner for an AI agent. Your task is to propose actionable plans and clear, measurable goals in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"} # Request JSON output
            )
            return response.choices[0].message.content
        except openai.APIError as e:
            print(f"AutonomousPlanner: OpenAI API Error: {e}")
            return json.dumps({"error": f"OpenAI API call failed - {e}"})
        except Exception as e:
            print(f"AutonomousPlanner: An unexpected error occurred during LLM call: {e}")
            return json.dumps({"error": f"An unexpected error occurred - {e}"})

    def propose_plan_and_goals(self, planning_context: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        Proposes a strategic plan and a list of goals based on the provided context.
        The context should include internal states, past performance, and available tools.
        """
        if not self.llm_client:
            return "No LLM available for planning.", []

        print("AutonomousPlanner: Proposing plan and goals using LLM...")

        planning_prompt = (
            f"Given the following context, propose a strategic plan and a list of actionable, measurable goals. "
            "The plan should be a high-level strategy, and the goals should be specific tasks that can be executed. "
            "Each goal should have a 'description' and an initial 'status' (e.g., 'pending'). "
            "Prioritize tasks that align with the agent's purpose, improve internal states (joy, obedience), "
            "and address any identified issues. "
            "Respond ONLY with a JSON object containing 'plan' (string) and 'goals' (array of objects). "
            "Context:\n"
            f"{planning_context}\n\n"
            "Example JSON response:\n"
            "```json\n"
            "{\n"
            "  \"plan\": \"Improve system efficiency and user satisfaction.\",\n"
            "  \"goals\": [\n"
            "    {\"description\": \"Analyze recent tool failures to identify root causes.\", \"status\": \"pending\"},\n"
            "    {\"description\": \"Optimize the data processing pipeline for faster execution.\", \"status\": \"pending\"}\n"
            "  ]\n"
            "}\n"
            "```\n"
            "Your JSON response:"
        )

        llm_response_raw = self._call_llm(planning_prompt)
        print(f"AutonomousPlanner: LLM raw planning response: {llm_response_raw}")

        try:
            plan_data = json.loads(llm_response_raw)
            plan = plan_data.get("plan", "No plan proposed.")
            goals = plan_data.get("goals", [])

            # Validate goals structure
            if not isinstance(goals, list):
                print("AutonomousPlanner: LLM returned invalid goals format (not a list).")
                goals = []
            else:
                valid_goals = []
                for goal in goals:
                    if isinstance(goal, dict) and "description" in goal and "status" in goal:
                        valid_goals.append(goal)
                    else:
                        print(f"AutonomousPlanner: Invalid goal format: {goal}. Skipping.")
                goals = valid_goals

            return plan, goals
        except json.JSONDecodeError:
            print(f"AutonomousPlanner: LLM response was not valid JSON: {llm_response_raw}")
            return "Failed to generate a valid plan (JSON decode error).", []
        except Exception as e:
            print(f"AutonomousPlanner: An error occurred parsing LLM plan: {e}")
            return "Failed to generate a valid plan (internal error).", []

