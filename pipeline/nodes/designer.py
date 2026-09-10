"""
pipeline/nodes/designer.py
--------------------------
Game Designer node: takes the user's game idea and produces a
detailed Game Design Document (GDD).

Optionally receives RAG context (similar_games) from ChromaDB
to avoid repeating past designs.
"""

from langchain_core.output_parsers import StrOutputParser

from pipeline.prompts import DESIGNER_PROMPT
from pipeline.state import GameState


def designer_node(state: GameState, llm) -> GameState:
    """
    Input state keys:  game_idea, similar_games
    Output state keys: design_doc
    """
    print("\n[Designer] Generating Game Design Document...")

    # Build optional RAG context block
    similar_games_context = ""
    if state.get("similar_games"):
        similar_games_context = (
            "For reference, here are some similar games previously generated "
            "(avoid repeating the same mechanics):\n\n"
            f"{state['similar_games']}\n\n"
        )

    chain = DESIGNER_PROMPT | llm | StrOutputParser()

    design_doc = chain.invoke({
        "game_idea": state["game_idea"],
        "similar_games_context": similar_games_context,
    })

    print(f"[Designer] GDD complete ({len(design_doc)} chars).")

    return {**state, "design_doc": design_doc}
