"""
ZUUP FORGE UI — VT100-era Control Plane
Serves the Forge dashboard with bitmap font aesthetic.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from forge.compiler.parser import load_all_specs

UI_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = UI_DIR.parent.parent  # zuup-forge/ (deployment root when Root Dir = zuup-forge)

app = FastAPI(
    title="ZUUP FORGE UI",
    description="The Platform That Builds Platforms — VT100 Control Plane",
    version="0.1.0",
)


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the Forge dashboard."""
    index_path = UI_DIR / "index.html"
    try:
        html = index_path.read_text(encoding="utf-8")
    except OSError:
        html = (
            "<!DOCTYPE html><html><head><title>ZUUP FORGE</title></head>"
            "<body><h1>ZUUP FORGE</h1><p>Dashboard unavailable.</p></body></html>"
        )
    return HTMLResponse(html)


@app.get("/api/platforms")
async def api_platforms():
    """List detected platforms from specs and generated code."""
    specs_dir = PROJECT_ROOT / "specs"
    platforms_dir = PROJECT_ROOT / "platforms"
    platforms = []

    # From specs
    if specs_dir.exists():
        try:
            specs = load_all_specs(specs_dir)
            for name, spec in specs.items():
                platforms.append({
                    "name": name,
                    "display_name": getattr(spec.platform, "display_name", name),
                    "domain": getattr(spec.platform, "domain", ""),
                    "description": getattr(spec.platform, "description", ""),
                })
        except Exception:
            pass

    # From generated platforms (may have more than specs)
    if platforms_dir.exists():
        for d in platforms_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                spec_json = d / "platform.spec.json"
                if spec_json.exists():
                    try:
                        import json
                        data = json.loads(spec_json.read_text(encoding="utf-8"))
                        p = data.get("platform", {})
                        existing = next((x for x in platforms if x["name"] == d.name), None)
                        if not existing:
                            platforms.append({
                                "name": d.name,
                                "display_name": p.get("display_name", d.name),
                                "domain": p.get("domain", ""),
                                "description": p.get("description", ""),
                            })
                    except Exception:
                        pass

    return {"platforms": platforms}


@app.get("/api/spec/{name}")
async def api_spec(name: str):
    """Return raw platform spec YAML content."""
    # Guard path: only allow simple names (no path traversal)
    if ".." in name or "/" in name or "\\" in name:
        return JSONResponse({"error": "Invalid spec name"}, status_code=400)
    spec_path = PROJECT_ROOT / "specs" / f"{name}.platform.yaml"
    if not spec_path.exists():
        return JSONResponse({"error": f"Spec not found: {name}"}, status_code=404)
    try:
        content = spec_path.read_text(encoding="utf-8")
    except OSError:
        return JSONResponse({"error": "Could not read spec"}, status_code=500)
    return {"content": content}


@app.get("/api/status/version")
async def api_version():
    """Return Forge version."""
    return {"version": "zuup-forge 0.1.0"}


@app.get("/api/deploy/{platform}")
async def api_deploy(platform: str):
    """Return deployment URLs and instructions for a platform."""
    if ".." in platform or "/" in platform or "\\" in platform:
        return JSONResponse({"error": "Invalid platform name"}, status_code=400)
    platforms_dir = PROJECT_ROOT / "platforms"
    if not (platforms_dir / platform).exists():
        return JSONResponse({"error": f"Platform not found: {platform}"}, status_code=404)
    # Deploy URLs (user connects repo; Render uses render.yaml at repo root)
    return {
        "platform": platform,
        "deploy": {
            "render": {
                "url": "https://dashboard.render.com/select-repo?type=blueprint",
                "instructions": "Connect your GitHub repo. Ensure render.yaml is at repo root. Set Root Directory to zuup-forge if prompted.",
            },
            "railway": {
                "url": "https://railway.app/new",
                "instructions": "New Project → Deploy from GitHub → select zuup-forge. Set Root Directory to zuup-forge. Use platforms/aureon/Dockerfile.",
            },
        },
    }


# Static files: served from public/static/ by Vercel CDN (see Vercel docs — do not mount here)
