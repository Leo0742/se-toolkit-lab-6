# Agent Documentation

## Overview

This project implements a minimal CLI agent that calls an LLM using an OpenAI-compatible API.

The agent accepts a question from the command line and returns a JSON response.

## Entry Point

agent.py

Example usage:

uv run agent.py "What is REST?"

## Configuration

The agent reads configuration from environment variables:

LLM_API_KEY
LLM_API_BASE
LLM_MODEL

These variables are loaded from:

.env.agent.secret

## Processing Flow

1. Read question from CLI
2. Load environment variables
3. Send request to LLM API
4. Extract assistant response
5. Print JSON

## Output Format

{
  "answer": "response text",
  "tool_calls": []
}

## Error Handling

If the question is missing or the API call fails, the program prints an error to stderr and exits with non-zero status.
