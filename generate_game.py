"""
generate_game.py
================
Uses a 3-agent CrewAI pipeline powered by the DeepSeek API to automatically
generate a single-file Pygame game from a plain-English idea.

Pipeline:
    1. Creative Game Designer  -> writes a Game Design Document
    2. Senior Python Developer -> writes the Pygame source code
    3. QA Engineer             -> reviews & fixes the code

Output:
    main.py  - the generated, syntax-checked Pygame game

Usage:
    1. Add your DeepSeek API key to a .env file:
           DEEPSEEK_API_KEY=sk-xxxxxxxxxxxx
    2. Install dependencies:
           pip install crewai litellm openai nest_asyncio
    3. Run:
           python generate_game.py

Change the `GAME_IDEA` constant below to generate a different game.
"""

# ---------------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------------
import asyncio
import os
import py_compile
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Windows: force UTF-8 output so emoji / box-drawing chars don't crash
# ---------------------------------------------------------------------------
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Configuration – edit these to customise the run
# ---------------------------------------------------------------------------
GAME_IDEA   = "Rotate a spaceship, shoot asteroids that split into smaller pieces, survive as long as you can"
OUTPUT_FILE = "spaceship.py"

# ---------------------------------------------------------------------------
# Step 1 – Load .env
# ---------------------------------------------------------------------------
def load_dotenv(path: Path) -> None:
    """Parse a .env file and inject each key into os.environ.
    Supports both KEY=value and KEY:value formats.
    """
    if not path.exists():
        print("[WARN] No .env file found – relying on existing environment variables.")
        return

    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
            elif ":" in line:
                key, value = line.split(":", 1)
            else:
                continue
            os.environ[key.strip()] = value.strip()

    print("[OK] .env loaded.")


load_dotenv(Path(__file__).parent / ".env")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise RuntimeError(
        "DEEPSEEK_API_KEY is not set. "
        "Add it to a .env file or export it as an environment variable."
    )
print(f"[OK] DEEPSEEK_API_KEY found (starts with: {DEEPSEEK_API_KEY[:8]}...)")

# ---------------------------------------------------------------------------
# Step 2 – Verify the DeepSeek API is reachable before starting the crew
# ---------------------------------------------------------------------------
print("\n[INFO] Testing DeepSeek API connection...")

from openai import OpenAI

_test_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
_test_resp   = _test_client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "Reply with exactly: DEEPSEEK CONNECTION OK"}],
    temperature=0,
    max_tokens=20,
)
print(f"[OK] API response: {_test_resp.choices[0].message.content}")

# ---------------------------------------------------------------------------
# Step 3 – Apply CrewAI / LiteLLM compatibility patches
# ---------------------------------------------------------------------------
import litellm
litellm.drop_params = True   # silently drop unsupported params instead of erroring

try:
    import crewai.llms.cache as _crewai_cache
    _crewai_cache.mark_cache_breakpoint = lambda msg: msg
    print("[OK] CrewAI cache patch applied.")
except (ImportError, AttributeError):
    pass   # older or newer CrewAI versions that don't need this patch

# ---------------------------------------------------------------------------
# Step 4 – Configure the shared LLM
# ---------------------------------------------------------------------------
from crewai import Agent, LLM

llm = LLM(
    model="deepseek/deepseek-chat",
    api_key=DEEPSEEK_API_KEY,
    temperature=0.2,
    max_tokens=6000,
)
print("[OK] LLM configured (DeepSeek / deepseek-chat).")

# ---------------------------------------------------------------------------
# Step 5 – Define the three agents
# ---------------------------------------------------------------------------
game_designer = Agent(
    role="Creative Game Designer",
    goal="Design fun, feasible 2D game concepts with clear mechanics.",
    backstory=(
        "You are an experienced game designer who turns vague ideas into "
        "detailed, exciting game designs: core loop, rules, win/lose conditions, "
        "entities, controls, and game feel. "
        "Keep the scope small enough to fit in a single-file Pygame game."
    ),
    verbose=True,
    llm=llm,
)

senior_engineer = Agent(
    role="Senior Python Game Developer",
    goal="Write clean, complete, runnable Pygame code for the designed game.",
    backstory=(
        "You are a senior Python engineer specialised in Pygame. "
        "You write well-structured code with a proper game loop, event handling, "
        "collision detection, scoring, and error-resistant logic. "
        "You always deliver a single self-contained Python file."
    ),
    verbose=True,
    llm=llm,
)

qa_engineer = Agent(
    role="QA Engineer & Code Reviewer",
    goal="Review and fix the game code so it is correct, complete, and playable.",
    backstory=(
        "You are a meticulous QA engineer. "
        "You check for syntax errors, runtime bugs, incomplete sections, "
        "and gameplay issues (collision logic, scoring, quit handling, etc.). "
        "You return the final corrected, complete code."
    ),
    verbose=True,
    llm=llm,
)

# ---------------------------------------------------------------------------
# Step 6 – Define the tasks (Design -> Code -> Review)
# ---------------------------------------------------------------------------
from crewai import Task

task_design = Task(
    description=(
        "Take the following game idea:\n\n"
        "  {game_idea}\n\n"
        "Expand it into a fun, simple 2D game design. "
        "Cover: objective, controls, entities, win/lose conditions, "
        "core mechanics, scoring system, and gameplay loop. "
        "Keep scope small enough for a single-file Pygame implementation.\n\n"
        "Output a clear Markdown Game Design Document."
    ),
    expected_output="A clear Markdown Game Design Document.",
    agent=game_designer,
)

task_code = Task(
    description=(
        "Using the Game Design Document from the previous task, write a COMPLETE "
        "standalone Python script using Pygame.\n\n"
        "Requirements:\n"
        "  - Include all necessary imports at the top.\n"
        "  - Use pygame, sys, random, and math as needed.\n"
        "  - Implement: pygame.init(), game loop, event handling, drawing, and scoring.\n"
        "  - The script must be entirely self-contained (no external assets).\n\n"
        "Wrap the final code in these exact markers:\n"
        "  FINAL_GAME_CODE_START\n"
        "  <your python code here>\n"
        "  FINAL_GAME_CODE_END"
    ),
    expected_output=(
        "A complete Python Pygame game script "
        "wrapped in FINAL_GAME_CODE_START / FINAL_GAME_CODE_END markers."
    ),
    agent=senior_engineer,
)

task_review = Task(
    description=(
        "Review the Pygame code from the previous task.\n"
        "Fix any syntax errors, logic bugs, missing initialisation, "
        "or incomplete sections.\n\n"
        "Return the FINAL corrected, complete Python script wrapped in:\n"
        "  FINAL_GAME_CODE_START\n"
        "  <corrected python code>\n"
        "  FINAL_GAME_CODE_END"
    ),
    expected_output=(
        "The final, corrected complete Python Pygame game "
        "wrapped in FINAL_GAME_CODE_START / FINAL_GAME_CODE_END markers."
    ),
    agent=qa_engineer,
)

# ---------------------------------------------------------------------------
# Step 7 – Assemble and run the crew
# ---------------------------------------------------------------------------
from crewai import Crew, Process

crew = Crew(
    agents=[game_designer, senior_engineer, qa_engineer],
    tasks=[task_design, task_code, task_review],
    process=Process.sequential,
    verbose=True,
)
print("[OK] Crew assembled. Starting generation...\n")

import nest_asyncio
nest_asyncio.apply()   # allows asyncio.run() inside environments that already have a loop

async def _run_crew():
    return await crew.kickoff_async(inputs={"game_idea": GAME_IDEA})

result     = asyncio.run(_run_crew())
raw_output = getattr(result, "raw", str(result))

print("\n" + "=" * 60)
print("FINAL CREW OUTPUT")
print("=" * 60)
print(raw_output)

# ---------------------------------------------------------------------------
# Step 8 – Extract the Python code from the crew output
# ---------------------------------------------------------------------------
def extract_game_code(text: str) -> str:
    """
    Pull the Python game code out of the crew's raw text response.
    Tries three strategies in order:
        1. Explicit FINAL_GAME_CODE_START … FINAL_GAME_CODE_END markers
        2. A fenced ```python … ``` block
        3. Raw text fallback if it looks like Pygame code
    """
    # Strategy 1: explicit markers
    marker = re.search(
        r"FINAL_GAME_CODE_START\s*(.*?)\s*FINAL_GAME_CODE_END",
        text, flags=re.DOTALL | re.IGNORECASE,
    )
    if marker:
        return marker.group(1).strip()

    # Strategy 2: fenced code block
    fenced = re.search(
        r"```(?:python|py)?\s*(.*?)```",
        text, flags=re.DOTALL | re.IGNORECASE,
    )
    if fenced:
        return fenced.group(1).strip()

    # Strategy 3: raw fallback
    if "import pygame" in text or "pygame.init()" in text:
        return text.strip()

    raise ValueError(
        "Could not extract Python game code from the crew output. "
        "Check the raw output printed above."
    )


game_code   = extract_game_code(raw_output)
output_path = Path(__file__).parent / OUTPUT_FILE
output_path.write_text(game_code, encoding="utf-8")
print(f"\n[OK] Game code saved to: {output_path}")

# ---------------------------------------------------------------------------
# Step 9 – Quick syntax check
# ---------------------------------------------------------------------------
try:
    py_compile.compile(str(output_path), doraise=True)
    print("[OK] Syntax check passed.")
except py_compile.PyCompileError as exc:
    print(f"[WARN] Syntax error in generated code: {exc}")
    print("       The file has been saved anyway – inspect and fix manually.")

print(f"\n[DONE] All done! Run:  python {OUTPUT_FILE}")
