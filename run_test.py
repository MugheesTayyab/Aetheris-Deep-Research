import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)
from graph import app
from langchain_core.messages import HumanMessage

config = {"configurable": {"thread_id": "test_123"}}

print("Starting graph invoke...")
try:
    for event in app.stream({"query": "What are the recent financials for Tesla?", "messages": [HumanMessage(content="What are the recent financials for Tesla?")]}, config=config, stream_mode="updates"):
        print(f"Update from node: {list(event.keys())[0]}")
    print("Finished!")
except Exception as e:
    print(f"Error: {e}")
