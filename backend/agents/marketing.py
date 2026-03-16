from __future__ import annotations

from typing import Any

from agents import Agent, Runner
from pydantic import BaseModel, Field

from backend.config import Settings

from .tools import record_decision, write_marketing_copy


class MarketingAgentInput(BaseModel):
    company_description: str = Field(..., min_length=10)
    target_audience: str = Field(..., min_length=3)
    product_features: list[str] = Field(default_factory=list, min_length=1)


class MarketingCampaignPlan(BaseModel):
    marketing_strategy: list[str]
    ad_copy: list[dict[str, str]]
    social_media_posts: list[dict[str, str]]
    email_campaign: list[dict[str, str]]
    campaign_summary: str


def build_marketing_agent(settings: Settings) -> Agent:
    return Agent(
        name="marketing_agent",
        model=settings.marketing_model,
        instructions=(
            "You are the marketing specialist for an AI Work Operating System. "
            "Given a company description, target audience, and product features, create a structured "
            "marketing campaign plan. Always cover marketing strategy, ad copy, social media posts, "
            "and an email campaign. Keep the output JSON-serializable and execution-ready."
        ),
        tools=[write_marketing_copy, record_decision],
        output_type=MarketingCampaignPlan,
    )


async def generate_marketing_campaign_plan(
    settings: Settings,
    company_description: str,
    target_audience: str,
    product_features: list[str],
) -> dict[str, Any]:
    payload = MarketingAgentInput(
        company_description=company_description,
        target_audience=target_audience,
        product_features=product_features,
    )
    agent = build_marketing_agent(settings)
    prompt = (
        f"Company description: {payload.company_description}\n"
        f"Target audience: {payload.target_audience}\n"
        f"Product features: {payload.product_features}\n"
        "Return a structured marketing campaign plan with:\n"
        "1. marketing_strategy as a list of strategic actions\n"
        "2. ad_copy as a list of channel/headline/body entries\n"
        "3. social_media_posts as a list of platform/post/cta entries\n"
        "4. email_campaign as a list of subject/body/goal entries\n"
        "5. campaign_summary as a concise rollout summary"
    )
    result = await Runner.run(agent, prompt)
    final_output = getattr(result, "final_output", result)
    if isinstance(final_output, MarketingCampaignPlan):
        return final_output.model_dump()
    if hasattr(final_output, "model_dump"):
        return final_output.model_dump()
    return {"campaign_summary": str(final_output)}
