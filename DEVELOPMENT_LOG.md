# Aetheris Deep Research - Development Log

This log documents the architecture, component design, and integration decisions made during the building of Aetheris Deep Research.

## 1. LangGraph State Machine

The core of the research agent is built using LangGraph's `StateGraph`. The graph orchestrates control flow between four specialized agent nodes (`Clarity`, `Research`, `Validator`, `Synthesis`) and a `Human Feedback` node, with conditional edges routing state dynamically based on metrics.

## 2. Clarity Agent Node

The Clarity Agent evaluates whether the user's research query contains a specific target company and an explicit goal. If vague, it sets the state to `needs_clarification` and triggers a Human-in-the-Loop interrupt.

## 3. Research Agent Node

The Research Agent uses Tavily Search API. It generates three independent search queries, gathers the web results, consolidates findings, and computes a 0-10 confidence score regarding information completeness.

## 4. Validator Agent Node

When search confidence is low (< 6), the Validator Agent reviews findings against the user's goal. It either marks them as `sufficient` or flags missing details as `insufficient`, looping back to research up to 3 times.

## 5. Synthesis Agent Node

The Synthesis Agent compiles the collected research findings and drafts the final markdown report. It structures findings with headings, bullet points, and source citations.

## 6. Graph State Definition (`state.py`)

The global graph state is defined as a `TypedDict` in `state.py`. It tracks the raw query, messages array, research findings, attempt counts, confidence scores, and clarity/validation statuses.

## 7. Human-in-the-Loop (HITL) Interrupts

We leverage LangGraph's `interrupt()` in `graph.py` to halt the state graph mid-execution when a query is unclear, persisting state parameters to the checkpoint database and waiting for user input.
