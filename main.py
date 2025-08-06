import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

from fastapi import FastAPI, Request  
from pydantic import BaseModel
import uvicorn
import requests

from app.agents.task_understanding_agent import generate_structured_prompt
from app.agents.subtask_distributor import agent as subtask_distributor_agent
from app.agents.prompt_refiner import PromptRefinerAgent
from app.agents.main_ss import SPARSystem
from app.agents.base_agent import SPARConfig

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

class FullPipelineRequest(BaseModel):
    user_prompt: str
    language: str = "python"
    refined_prompt: str = None

# Initialize SPAR System
spar_system = None

def get_spar_system():
    global spar_system
    if spar_system is None:
        config = SPARConfig()
        spar_system = SPARSystem(config)
    return spar_system

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

@app.post("/api/full-pipeline")
async def run_full_pipeline(request: FullPipelineRequest):
    """Run the complete SPAR pipeline including code generation, testing, and debugging"""
    try:
        spar = get_spar_system()
        result = spar.solve_problem(request.user_prompt, request.refined_prompt)
        return result
    except Exception as e:
        return {"error": str(e), "status": "failed"}

@app.post("/api/code-generation")
async def run_code_generation(request: PromptRequest):
    """Run only the code generation part"""
    try:
        spar = get_spar_system()
        code = spar.code_agent.generate_code(request.user_prompt)
        return {"code": code, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}

@app.post("/api/test-generation")
async def run_test_generation(request: dict):
    """Run test generation for given code"""
    try:
        spar = get_spar_system()
        problem = request.get("problem", "")
        code = request.get("code", "")
        test_cases = spar.tester.generate_tests(problem, code)
        return {"test_cases": test_cases, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}

@app.post("/api/run-tests")
async def run_tests(request: dict):
    """Run tests for given code"""
    try:
        spar = get_spar_system()
        code = request.get("code", "")
        test_cases = request.get("test_cases", [])
        test_results = spar.tester.run_tests(code, test_cases)
        return {"test_results": test_results, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}

@app.post("/api/debug-code")
async def debug_code(request: dict):
    """Debug and fix code"""
    try:
        spar = get_spar_system()
        problem = request.get("problem", "")
        code = request.get("code", "")
        error = request.get("error", "")
        test_cases = request.get("test_cases", [])
        debug_result = spar.debugger.debug_and_fix(problem, code, error, test_cases)
        return {"debug_result": debug_result, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)