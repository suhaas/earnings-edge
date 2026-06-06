# earnings-edge Architecture

## System Overview

earnings-edge is a multi-agent system orchestrated via LangGraph:

```
User Request
    ↓
Supervisor Agent (Routes to workers)
    ├→ Researcher Agent (Web search + RAG)
    ├→ Analyst Agent (Financial analysis)
    └→ Coder Agent (Code execution)
    ↓
Critic Agent (Evaluates output)
    ↓
Response
```

## Graph Topology

- **Nodes**: Agents (supervisor, researcher, analyst, coder, critic)
- **Edges**: Conditional handoffs (supervisor routes → worker → critic → feedback/end)
- **State**: Shared GraphState (messages, scratchpad, routing decision, budgets)
- **Persistence**: PostgreSQL checkpoints (resume, time-travel debugging)

## Key Components

- **Tools**: Atomic callables (web_search, code_exec, file_io, retrieval, etc.)
- **Skills**: Multi-step workflows (web_research, code_execution, file_io, api_integration, memory_management)
- **RAG**: Ingest → chunk → embed → hybrid retrieve + rerank
- **Observability**: LangSmith traces + OpenTelemetry + Prometheus metrics
- **Evaluation**: Versioned datasets + scorers + regression gate

## Deployment

- **Local**: `docker-compose up` (app + Postgres + Qdrant + OTel)
- **Production**: Docker image deployed to container registry
- **CI/CD**: GitHub Actions (lint → test → eval gate)
