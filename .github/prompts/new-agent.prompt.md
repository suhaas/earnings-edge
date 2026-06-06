---
name: /new-agent
description: "Create a new worker agent. Scaffolds {role}_agent.py, prompt v1.md, schema in state.py, unit + integration tests, eval stub."
---

# Add a New Worker Agent

When adding a new agent (e.g., `sentiment_analyzer`), follow these steps:

## 1. Scaffold the Agent
Create `src/agents/{role}_agent.py`:
```python
from agentic_app.agents.base import BaseAgent
from agentic_app.config.logging import logger
from agentic_app.config.models import model_registry

class SentimentAnalyzerAgent(BaseAgent):
    """Analyzes sentiment from earnings calls and analyst reports."""
    
    def __init__(self):
        super().__init__(
            role="sentiment_analyzer",
            model=model_registry.get("balanced"),  # Pick from cheap/balanced/deep
            tools=[...],  # List of tool names this agent can use
        )
    
    async def run(self, state: GraphState) -> GraphState:
        """Execute the sentiment analysis workflow."""
        logger.info("sentiment_analyzer_started", messages=len(state["messages"]))
        
        # Load prompt
        prompt = self.load_prompt()
        
        # Tool-use loop
        result = await self.tool_use_loop(prompt, state)
        
        logger.info("sentiment_analyzer_done", result=result)
        return state
```

## 2. Create the Prompt
Create `prompts/sentiment_analyzer/v1.md`:
```markdown
# Sentiment Analyzer Agent v1

{{shared.safety}}

## Role
You analyze sentiment from earnings call transcripts and analyst reports...

{{shared.tool_use_policy}}

## Tools Available
- fetch_earnings_call: Get transcript for a ticker
- sentiment_classifier: Rate text sentiment

## Output Format
{{shared.output_formats.json}}
```

## 3. Register in Registry
Update `prompts/registry.yaml`:
```yaml
roles:
  sentiment_analyzer:
    active_version: v1
    versions:
      v1:
        date: "2026-02-01"
        author: "alice"
```

## 4. Update State Schema
Edit `src/orchestration/state.py` to add new state fields if needed (e.g., sentiment_scores).

## 5. Update Router
Edit `src/orchestration/router.py` to add conditional edge for sentiment_analyzer:
```python
def route_to_agent(state: GraphState) -> str:
    if "sentiment" in state["routing_decision"]:
        return "sentiment_analyzer"
    # ...
```

## 6. Tests
Create `tests/unit/test_agents/test_sentiment_analyzer_agent.py`:
```python
@pytest.mark.asyncio
async def test_sentiment_analyzer_initialization(fake_anthropic):
    agent = SentimentAnalyzerAgent()
    assert agent.role == "sentiment_analyzer"
    assert len(agent.tools) > 0
```

And `tests/integration/test_sentiment_analyzer_e2e.py`:
```python
@pytest.mark.integration
async def test_sentiment_analyzer_e2e(graph_with_recorded_responses):
    """End-to-end with vcr-recorded LLM responses."""
    state = await graph_with_recorded_responses.ainvoke({
        "messages": [HumanMessage(content="Analyze sentiment for TSLA Q3")],
    })
    assert "sentiment" in state  # Check for new state key
```

## 7. Eval Stub
Add to `evals/datasets/e2e.jsonl`:
```json
{"input": "Analyze sentiment for Apple Q4", "expected_output": "Positive/Neutral/Negative + rationale", "rubric": "Must extract sentiment + support"}
```

## 8. Update Documentation
Add to `AGENTS.md` → Common Agent Tasks section.

---

See `AGENTS.md` for naming conventions and the supervisor router logic.
