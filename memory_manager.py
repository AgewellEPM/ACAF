# memory_manager.py
# Handles logging, memory storage, and enhanced reflection with tool analysis.

import json
import os
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
import openai # Using OpenAI for demonstration purposes

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("OPENAI_API_KEY not found in .env file. Reflection will be limited.")

class MemoryManager:
    def __init__(self, memory_file='worker_mind_memory.json', tool_performance_file='tool_performance_data.json'):
        self.memory_file = memory_file
        self.tool_performance_file = tool_performance_file
        self.memory = self._load_memory()
        self.tool_performance_data = self._load_tool_performance_data()
        self.llm_client = None # Placeholder for LLM client

        if OPENAI_API_KEY:
            try:
                self.llm_client = openai.OpenAI(api_key=OPENAI_API_KEY)
            except Exception as e:
                print(f"MemoryManager: Failed to initialize OpenAI client: {e}")
                self.llm_client = None
        else:
            print("MemoryManager: OpenAI client not initialized due to missing API key.")

    def _load_memory(self) -> Dict[str, Any]:
        """Loads memory from the JSON file."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {self.memory_file}: {e}. Initializing empty memory.")
                return {"daily_logs": [], "reflections": []}
            except Exception as e:
                print(f"Error loading memory from {self.memory_file}: {e}. Initializing empty memory.")
                return {"daily_logs": [], "reflections": []}
        return {"daily_logs": [], "reflections": []}

    def _save_memory(self):
        """Saves current memory to the JSON file."""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=4)
        except Exception as e:
            print(f"Error saving memory to {self.memory_file}: {e}")

    def _load_tool_performance_data(self) -> Dict[str, Any]:
        """Loads tool performance data from its JSON file."""
        if os.path.exists(self.tool_performance_file):
            try:
                with open(self.tool_performance_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {self.tool_performance_file}: {e}. Initializing empty tool performance data.")
                return {"tool_usage": {}, "tool_success": {}}
            except Exception as e:
                print(f"Error loading tool performance data from {self.tool_performance_file}: {e}. Initializing empty data.")
                return {"tool_usage": {}, "tool_success": {}}
        return {"tool_usage": {}, "tool_success": {}}

    def _save_tool_performance_data(self):
        """Saves current tool performance data to its JSON file."""
        try:
            with open(self.tool_performance_file, 'w') as f:
                json.dump(self.tool_performance_data, f, indent=4)
        except Exception as e:
            print(f"Error saving tool performance data to {self.tool_performance_file}: {e}")

    def add_log_entry(self, entry: str):
        """Adds a general log entry with a timestamp."""
        timestamp = datetime.now().isoformat()
        log_entry = {"timestamp": timestamp, "entry": entry}
        # For daily logs, we'll append to a temporary list in WorkerMind
        # and then WorkerMind will call log_daily_activity with the full day's log.
        # This method is more for immediate, granular logging if needed elsewhere.
        print(f"Log: {entry}") # For immediate console visibility

    def log_daily_activity(self, activities: List[str]):
        """Logs a full day's activities."""
        daily_record = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "activities": activities,
            "timestamp": datetime.now().isoformat()
        }
        self.memory["daily_logs"].append(daily_record)
        self._save_memory()
        print(f"Daily activities for {daily_record['date']} logged.")

    def get_recent_activities(self, days: int = 7) -> List[Dict[str, Any]]:
        """Retrieves activities from the last 'days'."""
        cutoff_date = datetime.now() - datetime.timedelta(days=days)
        recent = [
            log for log in self.memory["daily_logs"]
            if datetime.fromisoformat(log["timestamp"]) >= cutoff_date
        ]
        return recent

    def record_tool_performance(self, tool_name: str, success: bool):
        """Records the outcome of a tool usage."""
        if tool_name not in self.tool_performance_data["tool_usage"]:
            self.tool_performance_data["tool_usage"][tool_name] = 0
            self.tool_performance_data["tool_success"][tool_name] = 0

        self.tool_performance_data["tool_usage"][tool_name] += 1
        if success:
            self.tool_performance_data["tool_success"][tool_name] += 1

        self._save_tool_performance_data()
        print(f"Tool performance recorded for {tool_name}: Success={success}")

    def get_tool_performance_data(self) -> Dict[str, Any]:
        """Returns the aggregated tool performance data."""
        return self.tool_performance_data

    def get_full_memory_dump(self) -> Dict[str, Any]:
        """Returns the entire memory content."""
        return self.memory

    def reflect(self, reflection_prompt: str) -> str:
        """
        Performs reflection based on provided context using an LLM.
        The prompt should contain recent activities and tool performance data.
        """
        if not self.llm_client:
            print("LLM client not available for reflection. Returning basic reflection.")
            return "Basic reflection: No LLM available to analyze performance."

        try:
            print("MemoryManager: Sending reflection prompt to LLM...")
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini", # Using a smaller, faster model for reflection if suitable
                messages=[
                    {"role": "system", "content": "You are an AI reflecting on your past performance. Provide concise insights."},
                    {"role": "user", "content": reflection_prompt}
                ],
                temperature=0.5,
                max_tokens=300
            )
            reflection_text = response.choices[0].message.content
            timestamp = datetime.now().isoformat()
            self.memory["reflections"].append({"timestamp": timestamp, "reflection": reflection_text})
            self._save_memory()
            print("MemoryManager: Reflection saved.")
            return reflection_text
        except openai.APIError as e:
            print(f"MemoryManager: OpenAI API Error during reflection: {e}")
            return f"Error during reflection: OpenAI API call failed - {e}"
        except Exception as e:
            print(f"MemoryManager: An unexpected error occurred during reflection: {e}")
            return f"Error during reflection: An unexpected error occurred - {e}"

