import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import agent

def test_merge_conflict_question_uses_read_file(monkeypatch):
    responses = [
        {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": '{"path":"wiki/git-workflow.md"}',
                                },
                            }
                        ],
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "message": {
                        "content": '{"answer":"Edit the conflicting file, choose which changes to keep, then stage and commit.","source":"wiki/git-workflow.md#resolving-merge-conflicts"}'
                    }
                }
            ]
        },
    ]

    def fake_call_llm(messages):
        return responses.pop(0)

    monkeypatch.setattr(agent, "call_llm", fake_call_llm)

    question = "How do you resolve a merge conflict?"
    messages = agent.build_initial_messages(question)
    tool_calls_log = []

    for _ in range(agent.MAX_TOOL_CALLS + 1):
        data = agent.call_llm(messages)
        message = data["choices"][0]["message"]

        assistant_message = {
            "role": "assistant",
            "content": message.get("content") or "",
        }

        if "tool_calls" in message and message["tool_calls"]:
            assistant_message["tool_calls"] = message["tool_calls"]
            messages.append(assistant_message)

            for tool_call in message["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                args = {"path": "wiki/git-workflow.md"}
                result = "dummy wiki contents"

                tool_calls_log.append(
                    {"tool": tool_name, "args": args, "result": result}
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result,
                    }
                )
            continue

        content = message["content"]
        break

    assert "read_file" == tool_calls_log[0]["tool"]
    assert "wiki/git-workflow.md" in tool_calls_log[0]["args"]["path"]
    assert "wiki/git-workflow.md#resolving-merge-conflicts" in content


def test_wiki_listing_question_uses_list_files(monkeypatch):
    responses = [
        {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "list_files",
                                    "arguments": '{"path":"wiki"}',
                                },
                            }
                        ],
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "message": {
                        "content": '{"answer":"The wiki contains documentation files.","source":"wiki/index.md#overview"}'
                    }
                }
            ]
        },
    ]

    def fake_call_llm(messages):
        return responses.pop(0)

    monkeypatch.setattr(agent, "call_llm", fake_call_llm)

    question = "What files are in the wiki?"
    messages = agent.build_initial_messages(question)
    tool_calls_log = []

    for _ in range(agent.MAX_TOOL_CALLS + 1):
        data = agent.call_llm(messages)
        message = data["choices"][0]["message"]

        assistant_message = {
            "role": "assistant",
            "content": message.get("content") or "",
        }

        if "tool_calls" in message and message["tool_calls"]:
            assistant_message["tool_calls"] = message["tool_calls"]
            messages.append(assistant_message)

            for tool_call in message["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                args = {"path": "wiki"}
                result = "git-workflow.md\nindex.md"

                tool_calls_log.append(
                    {"tool": tool_name, "args": args, "result": result}
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result,
                    }
                )
            continue

        content = message["content"]
        break

    assert "list_files" == tool_calls_log[0]["tool"]
    assert tool_calls_log[0]["args"]["path"] == "wiki"
    assert "wiki/index.md#overview" in content
