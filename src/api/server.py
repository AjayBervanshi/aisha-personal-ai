import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# Ensure Aisha brain imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.aisha_brain import AishaBrain

app = FastAPI(title="Aisha Master Brain API")

# Add CORS to allow Lovable frontend to call this directly later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize one persistent Brain instance
aisha = AishaBrain()

class MessageHistory(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    message: str
    mode: Optional[str] = "auto"
    language: Optional[str] = "auto"
    history: Optional[List[MessageHistory]] = []

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        print(f"[API] Received message for Aisha: {req.message}")
        # Note: Ideally we pass mode/language/history into think(), but the current 
        # aisha.think() handles its own mood/lang detection and context loading right now.
        # We route this through the Heavy Python Brain.
        reply = aisha.think(req.message, platform="web")
        return {"reply": reply}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[API] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Aisha Heavy Python Brain is Online"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)
