"""Optional ADK newsroom workflow scaffold."""

from __future__ import annotations

try:
    from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
except ImportError:  # pragma: no cover - optional dependency
    LlmAgent = None
    ParallelAgent = None
    SequentialAgent = None


def build_newsroom_workflow(model_name: str = "gemini-2.0-flash"):
    """Create a newsroom workflow once google-adk is installed."""
    if not all((LlmAgent, ParallelAgent, SequentialAgent)):
        raise RuntimeError("google-adk is not installed. Run `pip install google-adk` first.")

    market_watch = LlmAgent(
        name="MarketWatch",
        model=model_name,
        instruction="Find the most important market-moving developments from the last 24 hours.",
        output_key="market_watch",
    )
    macro_watch = LlmAgent(
        name="MacroWatch",
        model=model_name,
        instruction="Find macro, rates, regulatory, and policy updates with likely market impact.",
        output_key="macro_watch",
    )
    narrative_watch = LlmAgent(
        name="NarrativeWatch",
        model=model_name,
        instruction="Find crypto and blockchain narratives with unusual momentum or mindshare.",
        output_key="narrative_watch",
    )
    ranker = LlmAgent(
        name="RankStories",
        model=model_name,
        instruction=(
            "Rank and deduplicate stories from {market_watch}, {macro_watch}, and {narrative_watch}. "
            "Prefer material novelty over repetition."
        ),
        output_key="ranked_stories",
    )
    script_writer = LlmAgent(
        name="WriteBroadcast",
        model=model_name,
        instruction=(
            "Write a spoken market bulletin from {ranked_stories}. Use the latest state to avoid repeating "
            "the same framing from prior segments."
        ),
        output_key="broadcast_script",
    )
    return SequentialAgent(
        name="NewsroomPipeline",
        sub_agents=[
            ParallelAgent(
                name="ResearchDesk",
                sub_agents=[market_watch, macro_watch, narrative_watch],
            ),
            ranker,
            script_writer,
        ],
    )
