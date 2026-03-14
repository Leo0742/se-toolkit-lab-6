import sys
import os
import json
import httpx
from dotenv import load_dotenv


# load secrets
load_dotenv(".env.agent.secret")


def call_llm(question: str) -> str:
    api_key = os.getenv("LLM_API_KEY")
    api_base = os.getenv("LLM_API_BASE")
    model = os.getenv("LLM_MODEL")

    if not api_key or not api_base or not model:
        raise RuntimeError("Missing LLM configuration")

    url = f"{api_base}/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": question}
        ]
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = httpx.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"].strip()


def main():
    if len(sys.argv) < 2:
        print("Usage: agent.py <question>", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    try:
        answer = call_llm(question)

        result = {
            "answer": answer,
            "tool_calls": []
        }

        print(json.dumps(result))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
