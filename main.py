from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

from app.agents.task_understanding_agent import generate_structured_prompt
from app.agents.subtask_distributor import router as std_router
from app.agents.prompt_refiner import router as pra_router

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Request models
# ---------------------------
class TUARequest(BaseModel):
    user_prompt: str
    language: str = "python"

# ---------------------------
# Routes
# ---------------------------
@app.post("/api/tua")
async def tua_endpoint(data: TUARequest):
    try:
        result = generate_structured_prompt(data.user_prompt, data.language)
        return result
    except Exception as e:
        logging.error("TUA endpoint error", exc_info=True)
        return {"error": str(e)}

# Mount STD & PRA routers
app.include_router(std_router, prefix="/api")
app.include_router(pra_router, prefix="/api")

@app.get("/")
async def root():
    return {"status": "Backend running"}
