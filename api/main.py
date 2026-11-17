import os
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def _load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
            elif ":" in line:
                k, _, v = line.partition(":")
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes.generate import router as generate_router
from api.routes.history  import router as history_router

app = FastAPI(
    title       = "IdeaToGame API",
    description = "Multi-agent AI pipeline that turns ideas into Pygame games",
    version     = "2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(generate_router, tags=["Generation"])
app.include_router(history_router,  tags=["History"])

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "2.0.0"}

# ---------------------------------------------------------------------------
# Static file serving — web_games directory (generated browser-playable games)
# ---------------------------------------------------------------------------
_project_root = Path(__file__).parent.parent
_web_games_dir = _project_root / "web_games"
_web_games_dir.mkdir(exist_ok=True)

app.mount("/web_games", StaticFiles(directory=str(_web_games_dir)), name="web_games")

# ---------------------------------------------------------------------------
# Serve React SPA build from ui/dist
# Must be mounted LAST so API routes take priority.
# ---------------------------------------------------------------------------
_ui_dist = _project_root / "ui" / "dist"

if _ui_dist.exists():
    # Mount assets directory for hashed JS/CSS bundles
    app.mount("/assets", StaticFiles(directory=str(_ui_dist / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str, request: Request):
        """Fall back to index.html for all non-API routes (React SPA routing)."""
        file_path = _ui_dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # SPA fallback
        return FileResponse(str(_ui_dist / "index.html"))
