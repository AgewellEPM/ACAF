# task_engine.py
# Manages sub-agents, task execution, tool use, and local KB queries.
# This is where the LLM would be heavily used to interpret tasks and select tools.

import json
import os
from typing import Tuple, Any
from dotenv import load_dotenv
import openai # Using OpenAI for demonstration purposes

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("OPENAI_API_KEY not found in .env file. Please set it.")
    # Fallback or raise error, depending on desired behavior
    # For this example, we'll proceed but LLM calls will fail.

from memory_manager import MemoryManager
from knowledge_base_manager import KnowledgeBaseManager
from tools import get_available_tools, Tool
from tool_api import call_tool

class TaskEngine:
    def __init__(self, memory_manager: MemoryManager, knowledge_base_manager: KnowledgeBaseManager):
        self.memory_manager = memory_manager
        self.knowledge_base_manager = knowledge_base_manager
        self.llm_client = None # Placeholder for LLM client

        if OPENAI_API_KEY:
            try:
                self.llm_client = openai.OpenAI(api_key=OPENAI_API_KEY)
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")
                self.llm_client = None
        else:
            print("OpenAI client not initialized due to missing API key.")

    def _call_llm(self, prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.7, max_tokens: int = 500) -> str:
        """Helper to call the LLM."""
        if not self.llm_client:
            print("LLM client not available. Cannot make LLM call.")
            return "Error: LLM client not configured."
        try:
            response = self.llm_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except openai.APIError as e:
            print(f"OpenAI API Error: {e}")
            return f"Error: OpenAI API call failed - {e}"
        except Exception as e:
            print(f"An unexpected error occurred during LLM call: {e}")
            return f"Error: An unexpected error occurred - {e}"

    def execute_task(self, task_description: str) -> Tuple[bool, str]:
        """
        Executes a given task description.
        This involves:
        1. Querying the local KB if relevant.
        2. Using an LLM to determine if a tool is needed or if the task can be completed directly.
        3. If a tool is needed, selecting the appropriate tool and its arguments.
        4. Calling the tool via tool_api.
        5. Recording tool performance.
        """
        print(f"TaskEngine: Attempting to execute task: '{task_description}'")
        task_log = {"task": task_description, "steps": []}

        # Step 1: Query local Knowledge Base
        kb_query_prompt = (
            f"Given the task '{task_description}', is there any relevant information or concept "
            "in the local knowledge base that could help in understanding or executing this task? "
            "If yes, provide a concise query for the knowledge base. If no, respond with 'N/A'."
            "Example: 'Query KB for concepts related to 'reinforcement learning'' or 'N/A'."
        )
        kb_query_suggestion = self._call_llm(kb_query_prompt, max_tokens=50)
        kb_info = ""
        if kb_query_suggestion and kb_query_suggestion.lower() != 'n/a':
            print(f"TaskEngine: LLM suggested KB query: '{kb_query_suggestion}'")
            # For simplicity, we'll just extract the query part. In a real system,
            # the LLM would output a structured JSON for tool calls.
            if "query kb for" in kb_query_suggestion.lower():
                query_text = kb_query_suggestion.lower().split("query kb for", 1)[1].strip().replace("'", "").replace('"', '')
                if query_text.endswith('.'):
                    query_text = query_text[:-1]
                kb_info = self.knowledge_base_manager.query_knowledge_base(query_text)
                task_log["steps"].append(f"KB Query: '{query_text}' -> Result: {kb_info[:100]}...")
                print(f"TaskEngine: KB query result: {kb_info[:100]}...")
            else:
                print("TaskEngine: LLM's KB query suggestion was not in the expected format.")
        else:
            print("TaskEngine: No relevant KB query suggested by LLM.")

        # Step 2: Determine action (tool use or direct response)
        available_tools = get_available_tools()
        tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in available_tools])

        action_prompt = (
            f"You are an agent designed to execute tasks. Given the task: '{task_description}'.\n"
            f"Context from Knowledge Base (if any):\n{kb_info}\n\n"
            f"Available Tools:\n{tool_descriptions}\n\n"
            "Based on the task and available tools, decide the best course of action. "
            "If a tool is suitable, provide a JSON object with 'tool_name' and 'tool_args'. "
            "Example: {'tool_name': 'search_web', 'tool_args': {'query': 'latest news'}}\n"
            "If no tool is suitable and you can directly answer or state the next logical step, "
            "provide a JSON object with 'direct_response' and 'response_content'. "
            "Example: {'direct_response': 'true', 'response_content': 'I will now proceed to...'}\n"
            "Ensure your response is a valid JSON object only."
        )

        llm_decision_raw = self._call_llm(action_prompt, model="gpt-4o-mini", max_tokens=200)
        print(f"TaskEngine: LLM raw decision: {llm_decision_raw}")

        try:
            llm_decision = json.loads(llm_decision_raw)
        except json.JSONDecodeError:
            print(f"TaskEngine: LLM response was not valid JSON: {llm_decision_raw}")
            task_log["steps"].append(f"LLM decision invalid JSON: {llm_decision_raw}")
            self.memory_manager.record_tool_performance("LLM_decision_parse", False)
            return False, "Failed to parse LLM's action decision."

        if "direct_response" in llm_decision and llm_decision.get("direct_response") == "true":
            response_content = llm_decision.get("response_content", "No specific content provided.")
            print(f"TaskEngine: LLM decided on direct response: {response_content}")
            task_log["steps"].append(f"Direct Response: {response_content}")
            self.memory_manager.record_tool_performance("LLM_direct_response", True)
            self.memory_manager.add_log_entry(f"Task '{task_description}' completed directly: {response_content}")
            return True, response_content
        elif "tool_name" in llm_decision and "tool_args" in llm_decision:
            tool_name = llm_decision["tool_name"]
            tool_args = llm_decision["tool_args"]
            print(f"TaskEngine: LLM decided to use tool '{tool_name}' with args: {tool_args}")
            task_log["steps"].append(f"Tool Call: {tool_name} with args {tool_args}")

            # Step 3 & 4: Call the tool
            tool_success = False
            tool_output = ""
            try:
                tool_output = call_tool(tool_name, **tool_args)
                tool_success = True
                print(f"TaskEngine: Tool '{tool_name}' executed successfully. Output: {tool_output[:100]}...")
                task_log["steps"].append(f"Tool Output: {tool_output[:100]}...")
            except Exception as e:
                tool_output = f"Error calling tool '{tool_name}': {e}"
                print(f"TaskEngine: {tool_output}")
                task_log["steps"].append(f"Tool Error: {tool_output}")

            # Step 5: Record tool performance
            self.memory_manager.record_tool_performance(tool_name, tool_success)
            self.memory_manager.add_log_entry(f"Task '{task_description}' attempted with tool '{tool_name}'. Success: {tool_success}. Output: {tool_output}")

            return tool_success, tool_output
        else:
            print(f"TaskEngine: LLM's decision was neither direct response nor tool call: {llm_decision_raw}")
            task_log["steps"].append(f"LLM decision unclear: {llm_decision_raw}")
            self.memory_manager.record_tool_performance("LLM_decision_unclear", False)
            return False, "LLM could not determine a clear action."

