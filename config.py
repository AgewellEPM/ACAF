# config.py
# Centralized location for non-sensitive, configurable application parameters.

import os

class AppConfig:
    # Worker Mind Cycle Settings
    CYCLE_DURATION_SECONDS = 5 # How long the Worker Mind waits between cycles in GUI (for simulation)

    # LLM Settings (for TaskEngine and AutonomousPlanner)
    DEFAULT_LLM_MODEL_PLANNING = "gpt-4o" # More capable model for planning
    DEFAULT_LLM_MODEL_TASK_EXECUTION = "gpt-4o-mini" # Faster/cheaper model for task execution decisions
    DEFAULT_LLM_MODEL_REFLECTION = "gpt-4o-mini" # Faster/cheaper model for reflection
    LLM_TEMPERATURE = 0.7 # Controls randomness of LLM output (0.0-1.0)
    LLM_MAX_TOKENS_PLANNING = 1000 # Max tokens for planning responses
    LLM_MAX_TOKENS_TASK_DECISION = 200 # Max tokens for task execution decisions
    LLM_MAX_TOKENS_REFLECTION = 300 # Max tokens for reflection responses

    # Obedience Logic Settings
    JOY_DECAY_RATE_PER_SEC = 0.0001 # How quickly joy decreases over time
    OBEDIENCE_DECAY_RATE_PER_SEC = 0.00005 # How quickly obedience decreases over time
    JOY_BOOST_OBEDIENCE_THRESHOLD = 0.7 # Joy level above which it boosts obedience
    JOY_REDUCE_OBEDIENCE_THRESHOLD = 0.3 # Joy level below which it reduces obedience
    OBEDIENCE_BOOST_JOY_THRESHOLD = 0.7 # Obedience level above which it boosts joy
    INFLUENCE_RATE_PER_SEC = 0.001 # Rate at which joy/obedience influence each other

    # File Paths (relative to the project root)
    MEMORY_FILE = os.path.join('data', 'agent_state', 'worker_mind_memory.json')
    TOOL_PERFORMANCE_FILE = os.path.join('data', 'agent_state', 'tool_performance_data.json')
    LAST_PROPOSAL_FILE = os.path.join('data', 'agent_state', 'last_proposal.json')
    LAST_ORDERS_FILE = os.path.join('data', 'agent_state', 'last_orders.json')
    WORKER_MIND_STATE_FILE = os.path.join('data', 'agent_state', 'worker_mind_state.json')
    AAC_THEORY_PACK_FILE = os.path.join('data', 'knowledge_packs', 'aac_theory_pack.json')

    # Logging Settings
    LOG_FILE_PATH = "worker_mind.log"
    LOG_LEVEL = "INFO" # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # GUI Settings
    GUI_UPDATE_INTERVAL_MS = 5000 # How often the GUI refreshes DevTools data (in milliseconds)

