# Agentic AI — Adaptive Execution System

## Architecture Overview

A four-agent system with an adaptive execution graph, dynamic replanning, risk prediction, tool marketplace, learning memory, and human-in-the-loop safety.

**Core Innovations:**
1. Adaptive Execution Graph (mutates at runtime)
2. Task Dependency Graph (parallelism discovery)
3. Parallel Execution Engine (concurrent task execution)
4. Risk Predictor (pre-execution risk assessment)
5. Tool Marketplace (metric-driven tool selection)
6. Learning Memory (persistent cross-session learning)
7. Human Approval Layer (approval gates)
8. Execution Ledger (transparent action logging)
9. Dynamic Replanning (intelligent failure recovery)
10. Adaptive Model Routing (cost-optimized LLM selection)

## File Tree

```
agentic-ai/
├── pyproject.toml
├── .env.example
├── README.md
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Central config (models, DB paths, API keys)
│   │   ├── models.py              # All Pydantic schemas
│   │   ├── state.py               # LangGraph state definitions
│   │   ├── constants.py           # Enums, literals, defaults
│   │   └── exceptions.py          # Custom exception types
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── supervisor.py          # Supervisor agent (state owner)
│   │   ├── planner.py             # Planner agent (DAG creator)
│   │   ├── worker.py              # Worker agent (universal executor)
│   │   └── evaluator.py           # Evaluator agent (score + replan)
│   │
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── state_machine.py       # LangGraph state machine graph
│   │   ├── dependency_graph.py    # Task dependency DAG builder
│   │   ├── execution_graph.py     # Adaptive execution DAG
│   │   ├── parallel_executor.py   # Parallel execution engine
│   │   └── scheduler.py           # Task scheduler with topological order
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py            # Tool registry & marketplace
│   │   ├── base_tool.py           # Base tool class
│   │   ├── flight_tool.py         # Flight search tool
│   │   ├── hotel_tool.py          # Hotel booking tool
│   │   ├── weather_tool.py        # Weather check tool
│   │   ├── train_tool.py          # Train/rail tool (fallback)
│   │   ├── budget_tool.py         # Budget calculator
│   │   └── email_tool.py          # Email summary tool
│   │
│   ├── risk/
│   │   ├── __init__.py
│   │   ├── risk_predictor.py      # Risk prediction engine
│   │   └── metrics.py             # Confidence / cost / security metrics
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── learning_memory.py     # ChromaDB-based learning store
│   │   ├── user_preferences.py    # User preference manager
│   │   └── plan_memory.py         # Past plan storage + recall
│   │
│   ├── ledger/
│   │   ├── __init__.py
│   │   ├── execution_ledger.py    # Action logging + transparency
│   │   └── ledger_entry.py        # Ledger entry schema
│   │
│   ├── approval/
│   │   ├── __init__.py
│   │   ├── approval_gate.py       # Human approval gate
│   │   └── approval_queue.py      # Queued approval requests
│   │
│   ├── model_routing/
│   │   ├── __init__.py
│   │   ├── router.py              # Adaptive model router
│   │   └── model_config.py        # Model capability/priority/cost mapping
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py              # FastAPI app
│   │   ├── routes.py              # API endpoints
│   │   ├── websocket_manager.py   # WebSocket streaming
│   │   └── schemas.py             # API request/response schemas
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # Logging config
│       └── helpers.py             # Misc helpers
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── Dashboard.tsx
│       │   ├── DAGView.tsx
│       │   ├── ExecutionLedger.tsx
│       │   ├── ApprovalGate.tsx
│       │   ├── RiskPanel.tsx
│       │   └── LiveTimeline.tsx
│       ├── hooks/
│       │   └── useWebSocket.ts
│       ├── api/
│       │   └── client.ts
│       └── styles/
│           └── globals.css
│
├── tests/
│   ├── test_state_machine.py
│   ├── test_dependency_graph.py
│   ├── test_parallel_executor.py
│   ├── test_risk_predictor.py
│   ├── test_tool_marketplace.py
│   └── test_demo_script.py
│
├── scripts/
│   └── demo.py                    # Demo script runner
│
└── data/
    ├── chroma_db/                 # ChromaDB persistent storage
    └── sqlite.db                  # SQLite database
```

## Data Models (Pydantic v2)

### Core State
```python
class TaskNode(BaseModel):
    id: str
    agent_type: Literal["planner", "worker", "evaluator"]
    status: TaskStatus  # pending, running, completed, failed, replanning
    input: dict
    output: dict | None
    dependencies: list[str]
    risk_assessment: RiskAssessment | None
    model_assigned: str | None
    created_at: datetime
    completed_at: datetime | None

class ExecutionGraph(BaseModel):
    nodes: dict[str, TaskNode]
    edges: list[tuple[str, str]]  # (from, to)
    status: GraphStatus
    metadata: dict

class AgentState(BaseModel):
    session_id: str
    user_goal: str
    constraints: dict
    execution_graph: ExecutionGraph
    current_phase: StatePhase
    ledger: list[LedgerEntry]
    approval_queue: list[ApprovalRequest]
    memory_context: dict
    errors: list[ExecutionError]
    final_summary: str | None
```

### Risk Assessment
```python
class RiskAssessment(BaseModel):
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    confidence: float  # 0-1
    failure_probability: float
    cost_estimate: float
    security_flags: list[str]
    requires_approval: bool
    reasoning: str
```

### Tool Marketplace
```python
class ToolMetrics(BaseModel):
    tool_name: str
    latency_ms: float
    accuracy: float  # 0-1
    failure_rate: float  # 0-1
    avg_cost: float
    last_used: datetime
    total_calls: int

class ToolRegistration(BaseModel):
    name: str
    description: str
    category: ToolCategory
    provider: str
    metrics: ToolMetrics
    input_schema: dict
    output_schema: dict
    fallback_chain: list[str]  # ordered fallback tools
```

### Execution Ledger
```python
class LedgerEntry(BaseModel):
    timestamp: datetime
    agent: str
    action: str
    task_id: str | None
    input_snapshot: dict | None
    output_snapshot: dict | None
    confidence: float
    latency_ms: float
    risk_level: str | None
```

### Learning Memory
```python
class MemoryEntry(BaseModel):
    id: str
    type: MemoryType  # tool_success, recovery_pattern, user_preference, failed_plan
    key: str
    value: dict
    embedding: list[float] | None
    timestamp: datetime
    session_id: str
    weight: float  # importance/relevance score
```

## State Machine

```
START → Understand Goal → Build DAG → Schedule Tasks → 
Parallel Execute → Evaluate → {Need Replan? YES → Update DAG → Continue}
                                     {NO → Approval → Summary → END}
```

### LangGraph State Flow
```
1. understand_goal()       → Supervisor interprets user goal
2. build_dag()             → Planner creates dependency + execution graph
3. schedule_tasks()        → Topological sort + parallel groups
4. parallel_execute()      → Execute ready tasks concurrently
5. evaluate_results()      → Evaluator scores output
6. decide_replan()         → Conditional: replan or proceed
7. update_dag()            → Replan: mutate graph, continue
8. approval_gate()         → Human-in-the-loop check
9. generate_summary()      → Final output
10. end()                  → Terminal state
```

## API Endpoints

```
POST   /api/session              # Create new session
GET    /api/session/{id}         # Get session state
POST   /api/session/{id}/goal    # Set user goal
POST   /api/session/{id}/start   # Start execution
GET    /api/session/{id}/graph   # Get current execution DAG
GET    /api/session/{id}/ledger  # Get execution ledger
GET    /api/session/{id}/status  # Get live status
POST   /api/approval/{id}/respond # Respond to approval request
GET    /api/tools                # List registered tools
GET    /api/tools/metrics        # Get tool marketplace metrics
WS     /ws/session/{id}          # WebSocket for live streaming

GET    /api/demo/script          # Get demo script
POST   /api/demo/run             # Run demo scenario
```

## Agent Contracts

### Supervisor
```
Input:  user_goal, constraints
Output: interpreted_goal, context, session_state
State:  owns all state, never calls external tools
```

### Planner
```
Input:  interpreted_goal, available_tools, memory_context
Output: dependency_graph (nodes + edges), execution_graph (ordered groups)
```

### Worker
```
Input:  task_node (type + input + assigned_model)
Process: calls tool → handles result/error
Output: task_output, success/failure, new_risk_context
```

### Evaluator
```
Input:  execution_graph, ledger, user_goal
Output: scores (correctness, completeness, safety), 
        replan_decision (yes/no), affected_tasks
```

## Component Interactions

```
User → FastAPI → Supervisor → Planner → Scheduler → 
  ┌──────────────────────────────┐
  │  Parallel Executor           │
  │  ├── Worker(Tool A) ───┐     │
  │  ├── Worker(Tool B) ───┤     │
  │  └── Worker(Tool C) ───┤     │
  │  ┌── Risk Predictor ◄──┘     │
  │  └── Tool Marketplace ◄──┘   │
  └──────────────────────────────┘
         ↓
  Evaluator → {Replan → Planner} or {Approval → Summary}
         ↓
  Execution Ledger (persisted) + Learning Memory (ChromaDB)
```

## Adaptive Model Routing

```
Agent Type      Primary Model    Fallback         Context
─────────────────────────────────────────────────────────
Planner         GPT-5.5          Qwen3            High reasoning needed
Risk Predictor  GPT-5.5-mini     Qwen3            Faster, cheaper
Worker          GPT-5.5-mini     Qwen3            High volume, diverse
Evaluator       GPT-5.5          Qwen3            Needs full context
Summary         Qwen3 (local)    GPT-5.5-mini     Cheap, simple
```

## Demo Script Flow

1. User: "Plan my Bangalore trip. Budget ₹30,000."
2. Planner → Dependency Graph appears
3. Parallel execution starts (Weather, Hotel, Flight)
4. Weather completes ✓ → Hotel completes ✓
5. Flight API returns 503
6. Risk Engine detects failure → Tool Marketplace switches provider
7. New flight found → Budget updated
8. Evaluator approves → Approval gate appears
9. User clicks Approve → Booking completes
10. Email sent → Execution Ledger displayed

## Implementation Phases

**Phase 1: Core Framework** (scaffolding, models, state machine)
**Phase 2: Agent System** (Supervisor, Planner, Worker, Evaluator)
**Phase 3: Execution Engine** (DAG builder, parallel executor, scheduler)
**Phase 4: Intelligence Layer** (Risk Predictor, Tool Marketplace, Model Router)
**Phase 5: Persistence** (Learning Memory, Execution Ledger)
**Phase 6: Safety** (Approval Gates, Error Recovery)
**Phase 7: API + UI** (FastAPI, WebSocket, React Dashboard)
**Phase 8: Demo** (Demo script, testing, polish)
