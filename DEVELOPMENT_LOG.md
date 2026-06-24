# Aetheris Deep Research - Development Log

This log documents the architecture, component design, and integration decisions made during the building of Aetheris Deep Research.

## 1. LangGraph State Machine

The core of the research agent is built using LangGraph's `StateGraph`. The graph orchestrates control flow between four specialized agent nodes (`Clarity`, `Research`, `Validator`, `Synthesis`) and a `Human Feedback` node, with conditional edges routing state dynamically based on metrics.

## 2. Clarity Agent Node

The Clarity Agent evaluates whether the user's research query contains a specific target company and an explicit goal. If vague, it sets the state to `needs_clarification` and triggers a Human-in-the-Loop interrupt.

## 3. Research Agent Node

The Research Agent uses Tavily Search API. It generates three independent search queries, gathers the web results, consolidates findings, and computes a 0-10 confidence score regarding information completeness.
