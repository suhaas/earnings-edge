# Runbook: Agent Stuck in Loop

## Scenario

An agent is stuck repeatedly calling the same tool or stuck in state.

## Diagnosis

1. **Check the trace** (LangSmith or local logs):
   ```bash
   scripts/replay_trace.py <trace_id>
   ```

2. **Look for**:
   - Same tool called repeatedly
   - step_count exceeding AGENT_MAX_STEPS
   - No progress on scratchpad

## Remediation

### Option 1: Temporary Step Limit

1. Set `AGENT_MAX_STEPS=3` in .env
2. Restart the app
3. The agent will exit after 3 steps

### Option 2: Manual State Edit

If using PostgreSQL checkpoints:
```sql
UPDATE langgraph_checkpoint 
SET data = jsonb_set(data, '{values, step_count}', '0')
WHERE checkpoint_ns = 'earnings-edge'
LIMIT 1;
```

### Option 3: Fix the Root Cause

1. **Identify the problem** (e.g., tool never returns success):
   - Edit the tool in `src/tools/`
   - Or edit the agent logic in `src/agents/`

2. **Run tests**:
   ```bash
   make test
   ```

3. **Validate with eval**:
   ```bash
   make eval
   ```

## Prevention

- Budget counters in graph state prevent infinite loops
- Tools must handle errors gracefully
- Supervisor checks routing decision at each step
