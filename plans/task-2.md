# Task 2 Plan

## Goal
Turn the CLI LLM client into a documentation agent that can inspect project files and answer documentation questions using tool calling.

## Tools
I will implement two tools:

1. list_files(path)
   - lists files and directories under a relative path
   - returns newline-separated entries

2. read_file(path)
   - reads a file under the project root
   - returns file contents as text

## Security
Both tools must reject access outside the project root.
I will normalize paths and verify that the resolved path stays inside the repository directory.

## Agentic loop
1. Send the user question and tool schemas to the LLM.
2. If the LLM returns tool calls, execute them.
3. Append tool results back into the conversation.
4. Repeat until the LLM returns a final answer without tool calls.
5. Stop after at most 10 tool calls.

## Output
The final JSON output will contain:
- answer
- source
- tool_calls

## Prompt strategy
The system prompt will instruct the model to:
- use list_files to discover wiki files
- use read_file to inspect relevant files
- include a source reference as file path plus section anchor

## Tests
I will add 2 regression tests:
- merge conflict question
- wiki listing question
