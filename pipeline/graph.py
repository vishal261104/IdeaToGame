"""
pipeline/graph.py
-----------------
Builds and compiles the LangGraph pipeline.

Graph flow:
    START
      │
      ▼
  [designer]  — writes Game Design Document
      │
      ▼
  [developer] — writes Pygame code
      │
      ▼
    [qa]      — reviews code + syntax check
      │
      ├── status == "success"  ──→ END
      ├── status == "retrying" ──→ [developer]  (retry loop, max 3)
      └── status == "failed"   ──→ END
"""

import os
from functools import partial
from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from pipeline.nodes.designer import designer_node
from pipeline.nodes.developer import developer_node
from pipeline.nodes.qa import qa_node
from pipeline.state import GameState


# ---------------------------------------------------------------------------
# Build shared LLM (DeepSeek via OpenAI-compatible client)
# ---------------------------------------------------------------------------
def _build_llm() -> ChatOpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not set. Check your .env file.")

    return ChatOpenAI(
        model="deepseek-chat",
        api_key=api_key,
        base_url="https://api.deepseek.com",
        temperature=0.2,
        max_tokens=6000,
    )


# ---------------------------------------------------------------------------
# Routing function — decides next node after QA
# ---------------------------------------------------------------------------
def _route_after_qa(state: GameState) -> str:
    if state["status"] == "success":
        return END
    if state["status"] == "retrying":
        return "developer"
    # "failed" — max retries exhausted
    return END


# ---------------------------------------------------------------------------
# Build the compiled graph
# ---------------------------------------------------------------------------
def build_graph():
    llm = _build_llm()

    # Bind LLM into each node via partial so nodes stay pure functions
    _designer  = partial(designer_node, llm=llm)
    _developer = partial(developer_node, llm=llm)
    _qa        = partial(qa_node, llm=llm)

    graph = StateGraph(GameState)

    graph.add_node("designer",  _designer)
    graph.add_node("developer", _developer)
    graph.add_node("qa",        _qa)

    graph.add_edge(START,       "designer")
    graph.add_edge("designer",  "developer")
    graph.add_edge("developer", "qa")

    # Conditional edge: QA can route to END or back to developer
    graph.add_conditional_edges("qa", _route_after_qa, {
        "developer": "developer",
        END:         END,
    })

    return graph.compile()


# ---------------------------------------------------------------------------
# Run the pipeline end-to-end
# ---------------------------------------------------------------------------
def run_pipeline(game_idea: str, output_file: str = "game.py") -> GameState:
    """
    Runs the full Designer → Developer → QA pipeline.
    Saves the generated code to `output_file` on success.
    Returns the final GameState.
    """
    graph = build_graph()

    initial_state: GameState = {
        "game_idea":    game_idea,
        "output_file":  output_file,
        "similar_games": "",
        "design_doc":   "",
        "game_code":    "",
        "dependencies": [],
        "description":  "",
        "retries":      0,
        "max_retries":  3,
        "syntax_error": "",
        "status":       "",
    }

    print(f"\n[Pipeline] Starting: '{game_idea}'")
    final_state = graph.invoke(initial_state)

    # Save generated code
    if final_state["game_code"]:
        output_path = Path(output_file)
        output_path.write_text(final_state["game_code"], encoding="utf-8")
        print(f"\n[Pipeline] Saved → {output_path.resolve()}")

    return final_state
