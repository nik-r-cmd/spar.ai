from fastapi import FastAPI, Request  
from pydantic import BaseModel
import uvicorn
import requests

from app.agents.task_understanding_agent import generate_structured_prompt
from app.agents.subtask_distributor import agent as subtask_distributor_agent
from app.agents.prompt_refiner import PromptRefinerAgent


app = FastAPI()

class PromptRequest(BaseModel):
    user_prompt: str
    language: str = "python"

class STDRequest(BaseModel):
    structured_prompt: str
    language: str = "python"

class PRARequest(BaseModel):
    tua: dict
    std: dict

# This function will call the Jupyter notebook's run_subtask_distributor via REST
def call_jupyter_subtask_distributor(structured_prompt):
    try:
        response = requests.post(
            "http://localhost:8888/run_subtask_distributor",
            json={"structured_prompt": structured_prompt},
            timeout=120
        )
        print("Jupyter response status:", response.status_code)
        print("Jupyter response text:", response.text)
        response.raise_for_status()
        try:
            return response.json()
        except Exception as e:
            print("Failed to parse JSON from Jupyter response:", e)
            return {"error": "Failed to parse Jupyter response", "raw": response.text}
    except Exception as e:
        print("Error calling Jupyter subtask distributor:", e)
        return {"error": str(e)}

@app.post("/api/tua")
async def run_tua(request: PromptRequest):
    task_data = {
        "original_prompt": request.user_prompt,
        "language": request.language,
    }
    structured = generate_structured_prompt(task_data)
    return structured

@app.post("/api/std")
async def run_std(request: STDRequest):
    input_dict = {
        "structured_prompt": request.structured_prompt,
        "language": request.language,
    }
    result = subtask_distributor_agent(input_dict)
    return {"std_result": result}

@app.post("/api/solve")
async def solve(request: PromptRequest):
    # 1. Run TaskUnderstandingAgent to get structured prompt
    task_data = {
        "original_prompt": request.user_prompt,
        "language": request.language,
    }
    print(f"[DEBUG] Prompt received by TUA: {task_data['original_prompt']}")
    structured = generate_structured_prompt(task_data)
    print(f"[DEBUG] TUA method_used: {structured.get('method_used','')}")
    # 2. Call the Jupyter agent
    result = call_jupyter_subtask_distributor(structured["structured_prompt"])
    return result
@app.post("/api/pra")
async def run_pra(request: PRARequest):
    print("[DEBUG] PRARequest received:", request)
    pra = PromptRefinerAgent()
    result = pra.refine(request.tua, request.std)
    print("[DEBUG] PRA result:", result)
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)