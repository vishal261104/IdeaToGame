# IdeaToGame 🎮

> Turn a plain-English game idea into a playable Pygame game using a 3-agent AI pipeline.

IdeaToGame uses **[CrewAI](https://crewai.com)** and the **[DeepSeek API](https://platform.deepseek.com)** to run three specialised AI agents back-to-back:

| Agent | Role |
|---|---|
| 🎨 Creative Game Designer | Writes a Game Design Document from your idea |
| 💻 Senior Python Developer | Implements the design as a single-file Pygame script |
| 🔍 QA Engineer | Reviews and fixes the code for correctness & playability |

The result is a ready-to-run `*.py` game file — no manual editing needed.

---

## Example Output

| Idea | Generated Game |
|---|---|
| "A fun endless runner where a character jumps over obstacles" | `main.py` — *Dash Runner* |
| "Rotate a spaceship, shoot asteroids that split into smaller pieces" | `spaceship.py` — *Asteroid Splitter* |

---

## Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/your-username/IdeaToGame.git
cd IdeaToGame
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Add your API key
Copy the example env file and fill in your [DeepSeek API key](https://platform.deepseek.com/api_keys):
```bash
cp .env.example .env
# then edit .env and paste your key
```

### 4. Set your game idea
Open `generate_game.py` and change the `GAME_IDEA` constant at the top:
```python
GAME_IDEA   = "Your game idea here"
OUTPUT_FILE = "my_game.py"
```

### 5. Generate & play
```bash
python generate_game.py   # generates the game
python my_game.py         # play it!
```

---

## Project Structure

```
IdeaToGame/
├── generate_game.py   # Main script — runs the AI pipeline
├── requirements.txt   # Python dependencies
├── .env.example       # API key template (copy to .env)
├── .gitignore
├── examples/
│   ├── main.py        # Example: Dash Runner (endless runner)
│   └── spaceship.py   # Example: Asteroid Splitter
└── README.md
```

---

## How It Works

```
Your idea (GAME_IDEA)
        │
        ▼
┌─────────────────────────┐
│  Creative Game Designer │  → Game Design Document (Markdown)
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│  Senior Python Developer│  → Single-file Pygame script
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│  QA Engineer            │  → Reviewed & fixed final code
└─────────────────────────┘
        │
        ▼
    OUTPUT_FILE.py  ← ready to run!
```

---

## Requirements

- Python 3.10+
- A free [DeepSeek API key](https://platform.deepseek.com/api_keys)

---

## Game Idea Suggestions

Paste any of these straight into `GAME_IDEA` to get started:

### 🕹️ Arcade Classics
| Idea | `GAME_IDEA` value |
|---|---|
| Brick Breaker | `"A brick breaker game with a paddle, bouncing ball, and colorful bricks that break on hit. Add a score and lives system."` |
| Snake | `"Classic snake game where the snake grows longer each time it eats food. Game over if it hits the wall or itself."` |
| Flappy Bird | `"A flappy bird clone where a rocket ship flies through space and must dodge incoming asteroid gaps."` |

### ⚔️ Action
| Idea | `GAME_IDEA` value |
|---|---|
| Space Invaders | `"Space invaders where waves of aliens descend toward the player. Player has a shield that degrades when hit."` |
| Vampire Survivors | `"Top-down survivor game where enemies swarm the player from all sides. Player auto-attacks. Collect XP gems to level up."` |
| Dungeon Crawler | `"Top-down dungeon crawler where the player fights skeletons, collects a key, and finds the exit door."` |

### 🧠 Puzzle / Casual
| Idea | `GAME_IDEA` value |
|---|---|
| Tower Stack | `"Stacking game where a platform swings back and forth and the player drops blocks to build the tallest tower."` |
| Gravity Flipper | `"A game where the player flips gravity with SPACE to navigate a character through a cave without hitting walls."` |
| Color Flood | `"A grid puzzle where the player floods the board from the top-left corner, trying to fill it all in one color in fewest moves."` |

---

## Tips

- **Change the game idea** by editing `GAME_IDEA` in `generate_game.py`
- **Generation takes 2–5 minutes** — the agents are making several LLM calls
- If the generated game has a syntax error, re-run `generate_game.py` (LLM outputs vary slightly)
- All games are self-contained — they only use `pygame`, `sys`, `math`, and `random`
- **Be descriptive** — the more detail in your idea, the better the output

---

## License

MIT — do whatever you want with the generated games.
