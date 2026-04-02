import os
import sys
import traceback
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional

# Ensure Aisha brain imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.aisha_brain import AishaBrain

app = FastAPI(title="Aisha Master Brain API")

# CORS — restrict to known origins in production
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Auth ──────────────────────────────────────────────────────────────────────

_security = HTTPBearer(auto_error=False)
_API_TOKEN = os.getenv("API_SECRET_TOKEN", "")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(_security)):
    """Require Bearer token on all API calls.  Set API_SECRET_TOKEN in .env."""
    if not _API_TOKEN:
        # No token configured → fail securely
        raise HTTPException(status_code=500, detail="Internal server error")
    if not credentials or credentials.credentials != _API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing API token")
    return True

# ── Rate Limiting (simple in-memory, swap for Redis in production) ─────────────

from collections import defaultdict
import time

_request_counts: dict = defaultdict(list)
_RATE_LIMIT = 20          # requests per window
_RATE_WINDOW = 60         # seconds

def rate_limit(request: Request):
    """Allow max 20 requests per IP per 60 seconds."""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - _RATE_WINDOW
    _request_counts[ip] = [t for t in _request_counts[ip] if t > window_start]
    if len(_request_counts[ip]) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")
    _request_counts[ip].append(now)

# ── Initialize Brain ─────────────────────────────────────────────────────────

aisha = AishaBrain()

# ── Models ───────────────────────────────────────────────────────────────────

class MessageHistory(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    message: str
    mode: Optional[str] = "auto"
    language: Optional[str] = "auto"
    history: Optional[List[MessageHistory]] = []

# ── Routes ───────────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat_endpoint(
    req: ChatRequest,
    _auth=Depends(verify_token),
    _rate=Depends(rate_limit),
):
    try:
        reply = aisha.think(req.message, platform="web")
        return {"reply": reply}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An internal server error occurred.")


@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Aisha Brain is Online"}


@app.get("/digest")
async def get_digest(_auth=Depends(verify_token), _rate=Depends(rate_limit)):
    """Return today's AI-generated digest."""
    try:
        from src.core.digest_engine import DigestEngine
        digest = DigestEngine(aisha.memory, aisha.ai).generate_daily_digest()
        return {"digest": digest}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An internal server error occurred.")


@app.get("/health-summary")
async def get_health_summary(_auth=Depends(verify_token), _rate=Depends(rate_limit)):
    """Return today's health tracking data."""
    try:
        from src.core.health_tracker import HealthTracker
        summary = HealthTracker(aisha.supabase).get_daily_summary()
        return summary
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An internal server error occurred.")


class HealthLogRequest(BaseModel):
    metric: str   # "water", "sleep", "workout"
    value: str    # e.g. "3", "7.5 good", "run 30"

@app.post("/log-health")
async def log_health(
    req: HealthLogRequest,
    _auth=Depends(verify_token),
    _rate=Depends(rate_limit),
):
    try:
        from src.core.health_tracker import HealthTracker
        tracker = HealthTracker(aisha.supabase)
        if req.metric == "water":
            tracker.log_water(int(req.value))
        elif req.metric == "sleep":
            parts = req.value.split()
            hours = float(parts[0])
            quality = parts[1] if len(parts) > 1 else "okay"
            tracker.log_sleep(hours, quality)
        elif req.metric == "workout":
            parts = req.value.split(maxsplit=1)
            tracker.log_workout(parts[0], parts[1] if len(parts) > 1 else "")
        return {"ok": True}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail="Invalid request data or format.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)
