"""Centralized agent constants — single source of truth for all magic numbers."""

# History / Context
MAX_HISTORY_TOKENS = 8000
MAX_HISTORY_COMPACT = 4000

# Guard
MAX_INPUT_LENGTH = 8192
MAX_CALLS_PER_TOOL = 30

# Execution / Loop
MAX_REFLECT_RETRIES = 3
MAX_LOOP_REPEAT = 3
MAX_DAG_TOTAL_SECONDS = 300
MAX_NODE_SECONDS = 120
MAX_ITERATIONS = 5
MAX_DAG_LOOP_ITERATIONS = 50  # Safety cap for ReAct loops in DAG nodes

# Memory TTLs (seconds)
SHORT_TERM_TTL = 3600
LONG_TERM_TTL = 2592000

# Cache
CACHE_TTL = 30
CACHE_DB = 5

# Dispatch
SUB_AGENT_TIMEOUT = 120
MAX_CONCURRENT_DISPATCH = 3
PEER_QUERY_TIMEOUT = 15

# ── State Management ──
STATE_TTL = 3600  # 1 hour — current state
SNAPSHOT_TTL = 86400  # 24 hours — state snapshots
STATE_MAX_VERSIONS = 50  # Max versions to retain per user
STATE_AUTO_SNAPSHOT = True  # Auto-snapshot before each DAG node

# ── Project Memory ──
PROJECT_MEMORY_TTL = 2592000  # 30 days (same as LONG_TERM_TTL)
PROJECT_MAX_ENTRIES = 100  # Max project-level entries per user
PROJECT_MAX_RECALL = 8  # Max project memories to inject into prompt

# ── Critic Agent ──
CRITIC_QUALITY_THRESHOLD = 0.7  # Min score to pass review
CRITIC_TIMEOUT = 30  # Max seconds for critic LLM call
CRITIC_MAX_RETRIES = 2

# ── Tool Router ──
MAX_TOOL_SCHEMAS = 15  # Max tool schemas to include per request
TOOL_ROUTE_CACHE_TTL = 60  # 1 minute tool route cache

# ── Model Router ──
MODEL_CHEAP = ""  # Set via env var: MODEL_CHEAP
MODEL_BALANCED = ""  # Set via env var: MODEL_BALANCED
MODEL_QUALITY = ""  # Set via env var: MODEL_QUALITY
MODEL_REASONING = ""  # Set via env var: MODEL_REASONING

# ── Strategic Reflexion ──
MAX_STRATEGIC_RETRIES = 2  # Max full-plan replan attempts
STRATEGIC_REFLECT_TIMEOUT = 30

# ── Multi-Agent Negotiation ──
NEGOTIATION_ROUNDS = 3  # Max proposal-critique rounds
NEGOTIATION_TIMEOUT = 60  # Per-round timeout seconds
CONSENSUS_THRESHOLD = 0.6  # Agreement threshold (0.0-1.0)
