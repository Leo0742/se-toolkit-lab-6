#!/usr/bin/env python3

# Simple repo + API exploration agent
# Leonid Bolbachan version

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

MAX_STEPS = 10
PROJECT_ROOT = Path(__file__).parent.resolve()


def load_env() -> dict[str, str]:
    env_file = Path(__file__).parent / ".env.agent.secret"

    if not env_file.exists():
        print("Missing .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    load_dotenv(env_file)

    docker_env = Path(__file__).parent / ".env.docker.secret"
    if docker_env.exists():
        load_dotenv(docker_env, override=False)

    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")

    lms_api_key = os.getenv("LMS_API_KEY")
    api_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")

    if not api_key or not api_base or not model:
        print("LLM config missing", file=sys.stderr)
        sys.exit(1)

    return {
        "api_key": api_key,
        "api_base": api_base.rstrip("/"),
        "model": model,
        "lms_api_key": lms_api_key or "",
        "agent_api_base_url": api_url.rstrip("/"),
    }


def validate_path(user_path: str) -> Path:
    if ".." in user_path:
        raise ValueError("Invalid path")

    full_path = (PROJECT_ROOT / user_path).resolve()

    if not str(full_path).startswith(str(PROJECT_ROOT)):
        raise ValueError("Outside project")

    return full_path


def read_file(path: str) -> str:
    try:
        file_path = validate_path(path)

        if not file_path.exists():
            return f"File not found: {path}"

        if not file_path.is_file():
            return f"Not a file: {path}"

        return file_path.read_text(encoding="utf-8")

    except Exception as e:
        return f"Read error: {e}"


def list_files(path: str) -> str:
    try:
        folder = validate_path(path)

        if not folder.exists():
            return f"Path missing: {path}"

        if not folder.is_dir():
            return f"Not directory: {path}"

        items = sorted([x.name for x in folder.iterdir()])
        return "\n".join(items)

    except Exception as e:
        return f"List error: {e}"


def query_api(
    method: str,
    path: str,
    body: str = "",
    skip_auth: bool = False,
    config: dict[str, str] | None = None,
) -> str:

    if config is None:
        return "Missing config"

    if ".." in path:
        return "Invalid path"

    if not path.startswith("/"):
        path = "/" + path

    url = f"{config['agent_api_base_url']}{path}"

    headers = {"Content-Type": "application/json"}

    if not skip_auth and config["lms_api_key"]:
        headers["Authorization"] = f"Bearer {config['lms_api_key']}"

    try:
        method = method.upper()

        with httpx.Client(timeout=30.0) as client:

            if method == "GET":
                r = client.get(url, headers=headers)

            elif method == "POST":
                r = client.post(url, headers=headers, content=body or "{}")

            elif method == "PUT":
                r = client.put(url, headers=headers, content=body or "{}")

            elif method == "DELETE":
                r = client.delete(url, headers=headers)

            else:
                return f"Unsupported method: {method}"

        result = {
            "status_code": r.status_code,
            "body": r.text,
        }

        return json.dumps(result)

    except Exception as e:
        return f"API error: {e}"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List directory",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call backend API",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string"},
                    "path": {"type": "string"},
                    "body": {"type": "string"},
                    "skip_auth": {"type": "boolean"},
                },
                "required": ["method", "path"],
            },
        },
    },
]


SYSTEM_PROMPT = """
You are an agent that explores a repository and a running backend.

Rules:

1. For documentation or wiki questions:
   - list_files
   - read_file

2. For source code questions:
   - list_files
   - read_file

3. For backend behaviour questions:
   - use query_api

4. For debugging:
   - query_api first
   - then inspect code

To discover routers:
list_files("backend/app/routers")

Final output must be JSON:

{"answer": "...", "source": "..."}
"""


def execute_tool(name: str, args: dict[str, Any], config: dict[str, str]) -> str:

    if name == "read_file":
        return read_file(args.get("path", ""))

    if name == "list_files":
        return list_files(args.get("path", ""))

    if name == "query_api":
        return query_api(
            args.get("method", "GET"),
            args.get("path", ""),
            args.get("body", ""),
            args.get("skip_auth", False),
            config,
        )

    return "Unknown tool"


def call_llm(messages: list[dict[str, Any]], config: dict[str, str]) -> dict[str, Any]:

    url = f"{config['api_base']}/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": config["model"],
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        "temperature": 0.7,
        "max_tokens": 2048,
    }

    with httpx.Client(timeout=60.0) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()

    data = r.json()
    msg = data["choices"][0]["message"]

    content = msg.get("content", "")
    tool_calls = []

    if "tool_calls" in msg:
        for tc in msg["tool_calls"]:
            tool_calls.append(
                {
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"],
                }
            )

    return {"content": content, "tool_calls": tool_calls}


def extract_source(log: list[dict[str, Any]]) -> str:

    for call in reversed(log):
        if call["tool"] == "read_file":
            return call["args"].get("path", "")

    return ""


def run_agentic_loop(question: str, config: dict[str, str]) -> dict[str, Any]:

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    tool_log = []

    for step in range(MAX_STEPS):

        print(f"Step {step+1}/{MAX_STEPS}", file=sys.stderr)

        response = call_llm(messages, config)

        if response["tool_calls"]:

            formatted = []

            for tc in response["tool_calls"]:
                formatted.append(
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    }
                )

            messages.append({"role": "assistant", "tool_calls": formatted})

            for tc in response["tool_calls"]:

                name = tc["name"]

                try:
                    args = json.loads(tc["arguments"])
                except Exception:
                    args = {}

                print(f"Tool: {name} {args}", file=sys.stderr)

                result = execute_tool(name, args, config)

                tool_log.append(
                    {"tool": name, "args": args, "result": result}
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    }
                )

        else:

            answer = response["content"]
            source = extract_source(tool_log)

            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_log,
            }

    return {"answer": "No result", "source": "", "tool_calls": tool_log}


def main():

    if len(sys.argv) < 2:
        print('Usage: uv run agent.py "question"', file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    config = load_env()

    result = run_agentic_loop(question, config)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
