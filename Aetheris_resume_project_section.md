Aetheris - Deep Research | AI Research Assistant
Tech Stack: Python, Streamlit, LangGraph, LangChain, Google Gemini, Tavily API

- Built an AI-powered deep research assistant that converts company and business research queries into structured, professional reports through a multi-agent workflow.
- Designed a LangGraph pipeline with separate clarity, research, validation, and synthesis agents to analyze user intent, gather web evidence, assess result quality, and generate final summaries.
- Integrated Tavily Search with Gemini models to retrieve live web results, score research confidence from 0-10, and retry low-confidence research paths before final synthesis.
- Added a human-in-the-loop clarification flow that pauses vague queries, asks follow-up questions, and resumes the same research session using graph checkpointing.
- Developed a polished Streamlit interface with session history, agent progress tracking, confidence indicators, synthesis metrics, and formatted research output cards.

