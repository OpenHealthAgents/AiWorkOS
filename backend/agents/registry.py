from __future__ import annotations

from agents import Agent

from backend.config import Settings

from .marketing import build_marketing_agent
from .tools import generate_code_scaffold, record_decision, web_research


def build_research_agent(settings: Settings) -> Agent:
    return Agent(
        name="research_agent",
        model=settings.research_model,
        instructions=(
            "You are the research specialist. Produce evidence-driven summaries, identify risks, "
            "and return concise findings with assumptions and next actions."
        ),
        tools=[web_research, record_decision],
    )


def build_coding_agent(settings: Settings) -> Agent:
    return Agent(
        name="coding_agent",
        model=settings.coding_model,
        instructions=(
            "You are the engineering specialist. Design implementation plans, API contracts, "
            "technical risks, and delivery-oriented build steps."
        ),
        tools=[generate_code_scaffold, record_decision],
    )


def build_orchestrator_agent(
    settings: Settings,
    research_agent: Agent,
    marketing_agent: Agent,
    coding_agent: Agent,
) -> Agent:
    return Agent(
        name="orchestrator_agent",
        model=settings.default_model,
        instructions=(
            "You are the workflow orchestrator for an AI Work Operating System. "
            "Route work to the best specialist, maintain execution order, and produce a unified outcome."
        ),
        handoffs=[research_agent, marketing_agent, coding_agent],
        tools=[record_decision],
    )


def build_agent_registry(settings: Settings) -> dict[str, Agent]:
    research_agent = build_research_agent(settings)
    marketing_agent = build_marketing_agent(settings)
    coding_agent = build_coding_agent(settings)
    orchestrator_agent = build_orchestrator_agent(
        settings=settings,
        research_agent=research_agent,
        marketing_agent=marketing_agent,
        coding_agent=coding_agent,
    )
    return {
        "orchestrator_agent": orchestrator_agent,
        "research_agent": research_agent,
        "marketing_agent": marketing_agent,
        "coding_agent": coding_agent,
    }
