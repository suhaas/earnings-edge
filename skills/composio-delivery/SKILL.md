---
name: composio-delivery
description: Delivers the finalized analyst brief to Slack, Notion, Google Sheets, and Gmail via authenticated Composio tools. Use whenever a completed, grounded brief must be distributed and logged.
---

# Delivery / Notification via Composio

## Purpose
Distribute the brief and append the signal to a tracking sheet.

## Inputs
- brief_markdown, signal, ticker/quarter, user_id

## Outputs
- delivery_log: list[str]  (per-channel status)

## Tools used
- Composio session tools bound to a create_agent ReAct loop:
  SLACK_SEND_MESSAGE, NOTION_ADD_PAGE_CONTENT, GOOGLESHEETS_BATCH_UPDATE, GMAIL_SEND_EMAIL.

## Agent responsible
Delivery agent.

## Procedure
1. `session = composio.create(user_id=user_id, toolkits=["slack","notion","googlesheets","gmail"])`.
2. `tools = session.tools()`; `agent = create_agent(model, tools=tools, system_prompt=...)`.
3. Instruct the agent (natural language) to post to #earnings, append a Sheets row, email,
   archive to Notion.
4. After success, write current-quarter tone to the Store (sentiment-surprise memory).

## Edge cases / notes
- First run per toolkit may require OAuth: `session.authorize(slug).redirect_url`,
  then `wait_for_connection()`.
- Make delivery idempotent (dedupe on f"{ticker}-{year}Q{quarter}") to avoid double posts on resume.
- Use lowercase slugs with sessions; uppercase with composio.tools.get.