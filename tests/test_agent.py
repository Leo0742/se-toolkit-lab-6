import json
import subprocess
import sys

def test_agent_output_structure():
    result = subprocess.run(
        [sys.executable, "agent.py", "Hello"],
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)

    assert "answer" in data
    assert "tool_calls" in data
