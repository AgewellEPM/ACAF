# The main GUI application for interacting with the Worker Mind.
# Provides user interaction, displays status, and includes a DevTools-like interface.

import tkinter as tk
from tkinter import scrolledtext, messagebox, END
import threading
import json
import os
import time
import logging

# Adjust path to import modules from src/
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

# Import core components from their new paths
from core.WorkerMindOrchestrator import WorkerMind
from core.AutonomousPlanner import AutonomousPlanner
from memory.AgentMemoryManager import MemoryManager
from core.ObedienceModule import ObedienceLogic
from agents.TaskExecutionEngine import TaskEngine
from knowledge_base.LocalKnowledgeBaseManager import KnowledgeBaseManager
from utils.logging_config import setup_logging # For centralized logging
from config import AppConfig # For configuration settings

# Setup logging for the GUI
setup_logging()
logger = logging.getLogger(__name__)

class WorkerMindDashboard:
    def __init__(self, master):
        self.master = master
        master.title("Worker Mind Dashboard")
        master.geometry("1000x800")

        # Ensure data directories exist
        os.makedirs(os.path.dirname(AppConfig.MEMORY_FILE), exist_ok=True)
        os.makedirs(os.path.dirname(AppConfig.AAC_THEORY_PACK_FILE), exist_ok=True)

        # Initialize core components with file paths from AppConfig
        self.memory_manager = MemoryManager(
            memory_file=AppConfig.MEMORY_FILE,
            tool_performance_file=AppConfig.TOOL_PERFORMANCE_FILE
        )
        self.obedience_logic = ObedienceLogic(state_file=AppConfig.WORKER_MIND_STATE_FILE)
        self.knowledge_base_manager = KnowledgeBaseManager(kb_file=AppConfig.AAC_THEORY_PACK_FILE)
        self.task_engine = TaskEngine(self.memory_manager, self.knowledge_base_manager)
        self.autonomous_planner = AutonomousPlanner(self.memory_manager)

        # Pass file paths for WorkerMind to load/save its state
        self.worker_mind = WorkerMind(
            self.memory_manager,
            self.obedience_logic,
            self.autonomous_planner,
            self.task_engine,
            last_proposal_file=AppConfig.LAST_PROPOSAL_FILE,
            last_orders_file=AppConfig.LAST_ORDERS_FILE
        )

        self.running = False
        self.worker_mind_thread = None

        self.create_widgets()
        self.load_initial_data() # Load any existing data on startup

    def create_widgets(self):
        # Main frames
        self.control_frame = tk.Frame(self.master, bd=2, relief="groove", padx=10, pady=10)
        self.control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.output_frame = tk.Frame(self.master, bd=2, relief="groove", padx=10, pady=10)
        self.output_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.devtools_frame = tk.Frame(self.master, bd=2, relief="groove", padx=10, pady=10)
        self.devtools_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # Control Frame Widgets
        tk.Label(self.control_frame, text="Worker Mind Controls", font=("Arial", 14, "bold")).pack(pady=5)

        self.start_button = tk.Button(self.control_frame, text="Start Worker Mind", command=self.start_worker_mind)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(self.control_frame, text="Stop Worker Mind", command=self.stop_worker_mind, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        tk.Label(self.control_frame, text="Manual Orders:").pack(side=tk.LEFT, padx=5)
        self.orders_entry = tk.Entry(self.control_frame, width=50)
        self.orders_entry.pack(side=tk.LEFT, padx=5)
        self.submit_orders_button = tk.Button(self.control_frame, text="Submit Orders", command=self.submit_manual_orders)
        self.submit_orders_button.pack(side=tk.LEFT, padx=5)

        # Output Frame Widgets
        tk.Label(self.output_frame, text="Worker Mind Output", font=("Arial", 12, "bold")).pack(pady=5)
        self.output_text = scrolledtext.ScrolledText(self.output_frame, wrap=tk.WORD, state=tk.DISABLED, height=15)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # Status indicators
        self.status_frame = tk.Frame(self.output_frame)
        self.status_frame.pack(fill=tk.X, pady=5)
        self.joy_label = tk.Label(self.status_frame, text="Joy: N/A", fg="blue")
        self.joy_label.pack(side=tk.LEFT, padx=10)
        self.obedience_label = tk.Label(self.status_frame, text="Obedience: N/A", fg="green")
        self.obedience_label.pack(side=tk.LEFT, padx=10)
        self.status_label = tk.Label(self.status_frame, text="Status: Idle", fg="gray")
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # DevTools Frame Widgets
        tk.Label(self.devtools_frame, text="DevTools", font=("Arial", 12, "bold")).pack(pady=5)

        self.devtools_notebook = tk.ttk.Notebook(self.devtools_frame)
        self.devtools_notebook.pack(fill=tk.BOTH, expand=True)

        # Memory Tab
        self.memory_tab = tk.Frame(self.devtools_notebook)
        self.devtools_notebook.add(self.memory_tab, text="Memory")
        self.memory_text = scrolledtext.ScrolledText(self.memory_tab, wrap=tk.WORD, state=tk.DISABLED)
        self.memory_text.pack(fill=tk.BOTH, expand=True)
        tk.Button(self.memory_tab, text="Refresh Memory", command=self.display_memory).pack(pady=5)

        # Tool Performance Tab
        self.tool_tab = tk.Frame(self.devtools_notebook)
        self.devtools_notebook.add(self.tool_tab, text="Tool Performance")
        self.tool_text = scrolledtext.ScrolledText(self.tool_tab, wrap=tk.WORD, state=tk.DISABLED)
        self.tool_text.pack(fill=tk.BOTH, expand=True)
        tk.Button(self.tool_tab, text="Refresh Tool Data", command=self.display_tool_performance).pack(pady=5)

        # Last Proposal Tab
        self.proposal_tab = tk.Frame(self.devtools_notebook)
        self.devtools_notebook.add(self.proposal_tab, text="Last Proposal")
        self.proposal_text = scrolledtext.ScrolledText(self.proposal_tab, wrap=tk.WORD, state=tk.DISABLED)
        self.proposal_text.pack(fill=tk.BOTH, expand=True)
        tk.Button(self.proposal_tab, text="Refresh Proposal", command=self.display_last_proposal).pack(pady=5)

        # KB Tab
        self.kb_tab = tk.Frame(self.devtools_notebook)
        self.devtools_notebook.add(self.kb_tab, text="Knowledge Base")
        self.kb_text = scrolledtext.ScrolledText(self.kb_tab, wrap=tk.WORD, state=tk.DISABLED)
        self.kb_text.pack(fill=tk.BOTH, expand=True)
        tk.Button(self.kb_tab, text="Refresh KB", command=self.display_knowledge_base).pack(pady=5)
        tk.Button(self.kb_tab, text="Load AAC Pack (Sim)", command=self.simulate_load_aac_pack).pack(pady=5)


    def load_initial_data(self):
        # Load last orders if available
        try:
            if os.path.exists(AppConfig.LAST_ORDERS_FILE):
                with open(AppConfig.LAST_ORDERS_FILE, 'r') as f:
                    data = json.load(f)
                    self.orders_entry.insert(0, data.get('orders', ''))
        except Exception as e:
            logger.error(f"Error loading {AppConfig.LAST_ORDERS_FILE}: {e}")
            self.log_output(f"Error loading last orders: {e}", "red")

        # Load AAC Theory Pack (simulated)
        self.simulate_load_aac_pack()


    def log_output(self, message, color="black"):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(END, message + "\n", color)
        self.output_text.see(END)
        self.output_text.config(state=tk.DISABLED)
        self.output_text.tag_config("red", foreground="red")
        self.output_text.tag_config("blue", foreground="blue")
        self.output_text.tag_config("green", foreground="green")
        self.output_text.tag_config("orange", foreground="orange")
        logger.info(message) # Also log to file

    def update_status_labels(self):
        self.joy_label.config(text=f"Joy: {self.obedience_logic.joy_level:.2f}")
        self.obedience_label.config(text=f"Obedience: {self.obedience_logic.obedience_level:.2f}")

    def start_worker_mind(self):
        if not self.running:
            self.running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text="Status: Running", fg="green")
            self.log_output("Worker Mind starting...", "blue")
            self.worker_mind_thread = threading.Thread(target=self.run_worker_mind_loop)
            self.worker_mind_thread.daemon = True # Allow thread to exit with main app
            self.worker_mind_thread.start()
            self.update_devtools_periodically()

    def stop_worker_mind(self):
        if self.running:
            self.running = False
            self.log_output("Worker Mind stopping...", "orange")
            # Give a moment for the loop to check self.running
            time.sleep(0.1)
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="Status: Stopped", fg="red")

    def run_worker_mind_loop(self):
        try:
            while self.running:
                self.log_output("\n--- Worker Mind Cycle Start ---", "blue")
                self.worker_mind.run_cycle()
                self.update_status_labels()
                self.log_output("--- Worker Mind Cycle End ---", "blue")
                time.sleep(AppConfig.CYCLE_DURATION_SECONDS)
        except Exception as e:
            logger.exception("An error occurred in Worker Mind loop:") # Log full traceback
            self.log_output(f"An error occurred in Worker Mind loop: {e}", "red")
            self.stop_worker_mind() # Stop on error

    def submit_manual_orders(self):
        orders = self.orders_entry.get()
        if orders:
            self.log_output(f"Manual Orders received: {orders}", "green")
            self.worker_mind.receive_manual_orders(orders)
            # Save last orders (now handled by WorkerMind)
            self.orders_entry.delete(0, END)
        else:
            messagebox.showwarning("Input Error", "Please enter some orders.")

    def update_devtools_periodically(self):
        if self.running:
            self.display_memory()
            self.display_tool_performance()
            self.display_last_proposal()
            self.display_knowledge_base()
            self.master.after(AppConfig.GUI_UPDATE_INTERVAL_MS, self.update_devtools_periodically)

    def _update_text_widget(self, text_widget, content):
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, END)
        text_widget.insert(END, content)
        text_widget.config(state=tk.DISABLED)

    def display_memory(self):
        try:
            memory_content = self.memory_manager.get_full_memory_dump()
            self._update_text_widget(self.memory_text, json.dumps(memory_content, indent=2))
        except Exception as e:
            logger.error(f"Error displaying memory: {e}")
            self._update_text_widget(self.memory_text, f"Error loading memory: {e}")

    def display_tool_performance(self):
        try:
            tool_data = self.memory_manager.get_tool_performance_data()
            self._update_text_widget(self.tool_text, json.dumps(tool_data, indent=2))
        except Exception as e:
            logger.error(f"Error displaying tool performance: {e}")
            self._update_text_widget(self.tool_text, f"Error loading tool performance data: {e}")

    def display_last_proposal(self):
        try:
            if os.path.exists(AppConfig.LAST_PROPOSAL_FILE):
                with open(AppConfig.LAST_PROPOSAL_FILE, 'r') as f:
                    proposal = json.load(f)
                    self._update_text_widget(self.proposal_text, json.dumps(proposal, indent=2))
            else:
                self._update_text_widget(self.proposal_text, "No last proposal found.")
        except Exception as e:
            logger.error(f"Error displaying last proposal from {AppConfig.LAST_PROPOSAL_FILE}: {e}")
            self._update_text_widget(self.proposal_text, f"Error loading last proposal: {e}")

    def display_knowledge_base(self):
        try:
            kb_content = self.knowledge_base_manager.get_knowledge_base_content()
            self._update_text_widget(self.kb_text, json.dumps(kb_content, indent=2))
        except Exception as e:
            logger.error(f"Error displaying knowledge base: {e}")
            self._update_text_widget(self.kb_text, f"Error loading knowledge base: {e}")

    def simulate_load_aac_pack(self):
        # Simulate loading the AAC theory pack into the KB
        try:
            if os.path.exists(AppConfig.AAC_THEORY_PACK_FILE):
                with open(AppConfig.AAC_THEORY_PACK_FILE, 'r') as f:
                    aac_data = json.load(f)
                    self.knowledge_base_manager.load_aac_pack(aac_data)
                    self.log_output("Simulated AAC Theory Pack loaded into KB.", "blue")
                    self.display_knowledge_base() # Refresh KB display
            else:
                self.log_output(f"{AppConfig.AAC_THEORY_PACK_FILE} not found. Creating a placeholder.", "orange")
                placeholder_data = {
                    "pack_name": "AAC Theory Basics",
                    "version": "1.0",
                    "concepts": [
                        {"id": "c1", "name": "Reinforcement", "description": "Process by which a stimulus increases the probability of a behavior."},
                        {"id": "c2", "name": "Punishment", "description": "Process by which a stimulus decreases the probability of a behavior."},
                        {"id": "c3", "name": "Shaping", "description": "Gradually molding a behavior by reinforcing successive approximations of the desired behavior."},
                        {"id": "c4", "name": "Extinction", "description": "The gradual weakening and disappearance of a conditioned response tendency."},
                        {"id": "c5", "name": "Generalization", "description": "The tendency for the conditioned stimulus to evoke similar responses after the response has been conditioned."},
                        {"id": "c6", "name": "Discrimination", "description": "The ability to perceive and respond to differences among stimuli."},
                        {"id": "c7", "name": "Prompting", "description": "A cue or assistance to encourage a desired response."},
                        {"id": "c8", "name": "Fading", "description": "The gradual removal of prompts or cues."},
                        {"id": "c9", "name": "Task Analysis", "description": "Breaking down a complex skill into smaller, teachable steps."},
                        {"id": "c10", "name": "ABC Data", "description": "Antecedent-Behavior-Consequence data collection for functional analysis."},
                    ],
                    "rules": [
                        {"id": "r1", "concept_ids": ["c1", "c2"], "rule": "Reinforcement increases behavior, punishment decreases it."},
                        {"id": "r2", "concept_ids": ["c3", "c9"], "rule": "Shaping is often used with task analysis to teach complex skills."},
                    ]
                }
                with open(AppConfig.AAC_THEORY_PACK_FILE, 'w') as f:
                    json.dump(placeholder_data, f, indent=4)
                self.knowledge_base_manager.load_aac_pack(placeholder_data)
                self.log_output("Placeholder aac_theory_pack.json created and loaded.", "blue")
                self.display_knowledge_base()

        except Exception as e:
            logger.error(f"Error simulating AAC pack load: {e}")
            self.log_output(f"Error simulating AAC pack load: {e}", "red")

def main():
    # Ensure necessary JSON files exist or are created as placeholders
    # These will be populated by the WorkerMind components at runtime
    # Using AppConfig paths
    for filename in [AppConfig.MEMORY_FILE, AppConfig.TOOL_PERFORMANCE_FILE,
                     AppConfig.LAST_PROPOSAL_FILE, AppConfig.LAST_ORDERS_FILE,
                     AppConfig.WORKER_MIND_STATE_FILE]:
        if not os.path.exists(filename):
            os.makedirs(os.path.dirname(filename), exist_ok=True) # Ensure directory exists
            with open(filename, 'w') as f:
                if filename == AppConfig.MEMORY_FILE:
                    json.dump({"daily_logs": [], "reflections": []}, f, indent=4)
                elif filename == AppConfig.TOOL_PERFORMANCE_FILE:
                    json.dump({"tool_usage": {}, "tool_success": {}}, f, indent=4)
                elif filename == AppConfig.LAST_PROPOSAL_FILE:
                    json.dump({"plan": "No plan yet.", "goals": []}, f, indent=4)
                elif filename == AppConfig.LAST_ORDERS_FILE:
                    json.dump({"orders": "", "timestamp": 0}, f, indent=4)
                elif filename == AppConfig.WORKER_MIND_STATE_FILE:
                    json.dump({"joy_level": 0.5, "obedience_level": 0.5, "last_update_time": datetime.now().isoformat()}, f, indent=4)

    # Check for aac_theory_pack.json specifically, as it's a source for KB
    if not os.path.exists(AppConfig.AAC_THEORY_PACK_FILE):
        # This will be handled by simulate_load_aac_pack when the GUI starts
        pass

    root = tk.Tk()
    app = WorkerMindDashboard(root)
    root.mainloop()

if __name__ == "__main__":
    from datetime import datetime # Import here if needed for main
    main()
