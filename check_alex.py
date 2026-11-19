"""check_alex.py - a 10-second health check for Alex.

Run it with:   .venv/bin/python check_alex.py
It tests each step Alex needs and tells you exactly which one fails.
"""
import os
from pathlib import Path

print("1. Looking for the .env file...")
env = Path(__file__).parent / ".env"
print("   found" if env.exists() else "   NOT FOUND: create a file named .env next to this one")

print("2. Reading the key...")
from dotenv import load_dotenv
load_dotenv(env)
key = os.environ.get("GROQ_API_KEY", "")
print("   key found, starts with", key[:4] + "..." if key else "   MISSING: .env needs a line like GROQ_API_KEY=gsk_...")
if not key:
    raise SystemExit

print("3. Asking the AI a simple question...")
import agent
llm = agent.get_llm()
print("   model:", agent.MODEL)
print("   AI says:", llm.invoke("Reply with just the word: ready").content)

print("4. Running Alex as an agent (he should look up the Tacoma with a tool)...")
result = agent.run_agent(llm, "Can I tow a small boat with the Toyota Tacoma?", [], {})
print("   tools used:", [s["tool"] for s in result["steps"]])
print("   Alex says:", result["reply"])
print("\nAll good!" if result["steps"] else "\nAlex answered without a tool. That works, but tell me so I can tune him.")
