# Task 1 Plan

## Goal
Implement a minimal CLI agent that accepts a question from the command line, sends it to an LLM, and prints a JSON response.

## Steps
1. Read the user question from sys.argv
2. Load LLM_API_KEY, LLM_API_BASE, LLM_MODEL from .env.agent.secret
3. Send a request to the OpenAI-compatible /chat/completions endpoint
4. Extract assistant text from the response
5. Print JSON object:
{
  "answer": "...",
  "tool_calls": []
}
6. On error print message to stderr and exit with non-zero code
