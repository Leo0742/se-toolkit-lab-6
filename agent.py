import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
MAX_TOOL_CALLS = 10

load_dotenv(PROJECT_ROOT / ".env.agent.secret")


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def resolve_safe_path(relative_path: str) -> Path:
    if not relative_path:
        raise ValueError("Path must not be empty")

    target = (PROJECT_ROOT / relative_path).resolve()

    try:
        target.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError("Access outside project root is not allowed") from exc

    return target


def list_files(path: str) -> str:
    try:
        target = resolve_safe_path(path)
        if not target.exists():
            return f"ERROR: path does not exist: {path}"
        if not target.is_dir():
            return f"ERROR: path is not a directory: {path}"

        entries = sorted(p.name for p in target.iterdir())
        return "\n".join(entries)
    except Exception as exc:
        return f"ERROR: {exc}"


def read_file(path: str) -> str:
    try:
        target = resolve_safe_path(path)
        if not target.exists():
            return f"ERROR: file does not exist: {path}"
        if not target.is_file():
            return f"ERROR: path is not a file: {path}"

        return target.read_text(encoding="utf-8")
    except Exception as exc:
        return f"ERROR: {exc}"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories under a relative path inside the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from the project root"
                    }
                },
                "required": ["path"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from the repository using a relative path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path from the project root"
                    }
                },
                "required": ["path"],
                "additionalProperties": False
            }
        }
    }
]


def execute_tool(name: str, args: dict) -> str:
    if name == "list_files":
        return list_files(args.get("path", ""))
    if name == "read_file":
        return read_file(args.get("path", ""))
    return f"ERROR: unknown tool: {name}"


def call_llm(messages: list[dict]) -> dict:
    api_key = require_env("LLM_API_KEY")
    api_base = require_env("LLM_API_BASE").rstrip("/")
    model = require_env("LLM_MODEL")

    url = f"{api_base}/chat/completions"

    payload = {
        "model": model,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    response = httpx.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def build_initial_messages(question: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "You are a documentation agent for this repository. "
                "Use the available tools to inspect repository documentation. "
                "Prefer list_files first, then read_file. "
                "Answer with repository-based information only. "
                "Return a final answer and include a source in the format "
                "'wiki/file.md#section-anchor'."
            ),
        },
        {
            "role": "user",
            "content": question,
        },
    ]


def main() -> int:
    if len(sys.argv) < 2:
        eprint('Usage: uv run agent.py "Your question here"')
        return 1

    question = sys.argv[1].strip()
    if not question:
        eprint("Question must not be empty")
        return 1

    messages = build_initial_messages(question)
    tool_calls_log = []
    final_answer = ""
    final_source = ""

    try:
        for _ in range(MAX_TOOL_CALLS):
            data = call_llm(messages)
            message = data["choices"][0]["message"]

            assistant_message = {
                "role": "assistant",
                "content": message.get("content") or "",
            }

            tool_calls = message.get("tool_calls", [])

            if tool_calls:
                assistant_message["tool_calls"] = tool_calls
                messages.append(assistant_message)

                for tool_call in tool_calls:
                    tool_name = tool_call["function"]["name"]
                    raw_args = tool_call["function"]["arguments"]
                    args = json.loads(raw_args) if raw_args else {}

                    result = execute_tool(tool_name, args)

                    tool_calls_log.append(
                        {
                            "tool": tool_name,
                            "args": args,
                            "result": result,
                        }
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result,
                        }
                    )

                continue

            content = (message.get("content") or "").strip()

            if content:
                try:
                    parsed = json.loads(content)
                    final_answer = parsed.get("answer", "").strip()
                    final_source = parsed.get("source", "").strip()
                except json.JSONDecodeError:
                    final_answer = content
                    final_source = "wiki/unknown.md#unknown"

            break

        if not final_answer:
            final_answer = "I could not find a final answer."
        if not final_source:
            final_source = "wiki/unknown.md#unknown"

        result = {
            "answer": final_answer,
            "source": final_source,
            "tool_calls": tool_calls_log,
        }

        print(json.dumps(result, ensure_ascii=False))
        return 0

    except Exception as exc:
        eprint(f"Agent error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
