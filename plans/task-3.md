# Task 3 Plan

## Goal
Extend the documentation agent with a new tool `query_api` so it can answer questions about the running system.

## Implementation plan
1. Load local environment from `.env.agent.secret` and `.env.docker.secret`.
2. Read configuration only from environment variables:
   - LLM_API_KEY
   - LLM_API_BASE
   - LLM_MODEL
   - LMS_API_KEY
   - AGENT_API_BASE_URL
3. Add tool schema `query_api(method, path, body?)`.
4. Implement HTTP call using httpx.
5. Use Authorization header:
   Bearer LMS_API_KEY
6. Default API base URL:
   http://localhost:42002
7. Update system prompt so the agent knows when to use:
   - read_file
   - list_files
   - query_api
8. Make `source` optional for system answers.
9. Add two regression tests for:
   - read_file usage
   - query_api usage
10. Run:
    uv run pytest tests -q
11. Run:
    uv run run_eval.py

## First benchmark run
TBD

## Iteration strategy
TBD
