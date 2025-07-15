# Requirements: fastapi, pydantic, uvicorn, requests
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import requests

from app.agents.task_understanding_agent import generate_structured_prompt

app = FastAPI()

class PromptRequest(BaseModel):
    user_prompt: str
    language: str = "python"

# This function will call the Jupyter notebook's run_subtask_distributor via REST
# Make sure your Jupyter notebook exposes this endpoint (see previous instructions)
def call_jupyter_subtask_distributor(structured_prompt):
    response = requests.post(
        "http://localhost:8888/run_subtask_distributor",
        json={"structured_prompt": structured_prompt},
        timeout=120
    )
    response.raise_for_status()
    return response.json()

@app.post("/api/solve")
async def solve(request: PromptRequest):
    # 1. Run TaskUnderstandingAgent to get structured prompt
    task_data = {
        "original_prompt": request.user_prompt,
        "language": request.language,
    }
    structured = generate_structured_prompt(task_data)
    # 2. Call the Jupyter agent
    result = call_jupyter_subtask_distributor(structured["structured_prompt"])
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)