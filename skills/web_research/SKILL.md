---
name: web_research
description: "Multi-step web research workflow: query formulation, source ranking, extraction, synthesis. Use when: agents need to gather earnings data, analyst reports, market sentiment, SEC filings, or other web-sourced information."
---

# Web Research Skill

This skill guides agents through structured web research for financial data, earnings, and market analysis.

## When to Use

- Gathering earnings data (revenue, EPS, guidance)
- Collecting analyst reports and ratings
- Retrieving SEC filings (10-K, 10-Q, 8-K)
- Researching market sentiment and commentary
- Finding historical stock data and comparables

## Workflow

### 1. Query Formulation
- **Clarify intent**: What's the specific question? (e.g., "Q3 2024 revenue for MSFT")
- **Refine**: Break broad queries into specific, searchable sub-queries
- **Source selection**: Choose sources (SEC EDGAR, FinTech APIs, news sites, earnings call transcripts)

### 2. Retrieval & Ranking
- **Search**: Use web search or RAG retrieval tools with specific queries
- **Filter**: Rank results by recency, authority, and relevance
- **Prioritize**: SEC filings over news; official sources over commentary

### 3. Extraction
- **Parse**: Extract key data points (dates, numbers, ratios, guidance)
- **Validate**: Cross-check figures across sources
- **Contextualize**: Note assumptions and caveats (e.g., "adjusted vs. reported EPS")

### 4. Synthesis
- **Aggregate**: Combine findings into a coherent narrative
- **Cite sources**: Include URLs/references for each claim
- **Flag gaps**: Note missing data (e.g., "guidance not provided")

## Tools Available

- `web_search`: General search; results include URLs and snippets
- `fetch_sec_filing`: Retrieve SEC documents by ticker and filing type
- `fetch_earnings_call_transcript`: Get earnings call transcript for a date
- `retrieval`: RAG query over ingested documents (faster if pre-indexed)

## Output Format

```json
{
  "query": "Q3 2024 earnings for Microsoft",
  "findings": [
    {
      "metric": "Revenue",
      "value": "$56.3B",
      "source": "SEC 10-Q filing",
      "url": "https://..."
    }
  ],
  "synthesis": "Microsoft reported...",
  "confidence": "high",
  "gaps": []
}
```

## Common Pitfalls

- **Outdated data**: Always check publication dates; skip stale articles
- **Unaudited claims**: Prefer official sources (SEC filings, investor relations)
- **Context collapse**: Don't mix quarterly and annual figures
- **Attribution**: Always cite the source for specific numbers

## Next Steps

See `AGENTS.md` → Researcher Agent role for how this skill integrates with the graph.
