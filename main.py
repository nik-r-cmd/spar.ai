import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import logging

from app.agents.task_understanding_agent import generate_structured_prompt
from app.agents.subtask_distributor import agent as subtask_distributor_agent
from app.agents.prompt_refiner import PromptRefinerAgent
from app.agents.main_ss import SPARSystem
from app.agents.base_agent import SPARConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# ---------- Request Models ----------
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
    signature: str = None
    edge_cases: str = None

# ---------- SPAR System Singleton ----------
spar_system = None
def get_spar_system():
    global spar_system
    if spar_system is None:
        config = SPARConfig()
        spar_system = SPARSystem(config)
    return spar_system

# ---------- Individual Endpoints ----------
@app.post("/api/tua")
async def run_tua(request: PromptRequest):
    task_data = {"original_prompt": request.user_prompt, "language": request.language}
    structured = generate_structured_prompt(task_data)
    logger.info(f"TUA output: {structured}")
    return structured

@app.post("/api/std")
async def run_std(request: STDRequest):
    input_dict = {
        "structured_prompt": request.structured_prompt,
        "language": request.language,
    }
    result = subtask_distributor_agent(input_dict)
    logger.info(f"STD output: {result}")
    return {"std_result": result}

@app.post("/api/pra")
async def run_pra(request: PRARequest):
    logger.info(f"PRARequest received: {request}")
    pra = PromptRefinerAgent()
    # Unwrap std_result if needed
    std_data = request.std.get("std_result", request.std)
    result = pra.refine(request.tua, std_data)
    logger.info(f"PRA result: {result}")
    return result

# ---------- Full Pipeline (Fixed) ----------
@app.post("/api/full-pipeline")
async def run_full_pipeline(request: FullPipelineRequest):
    """Run the complete SPAR pipeline including code generation, testing, and debugging"""
    logger.info(f"Full pipeline request received: {request.dict()}")
    try:
        spar = get_spar_system()

        # Check if refined_prompt is provided, otherwise run TUA/STD/PRA
        if request.refined_prompt:
            logger.info("Using provided refined_prompt, skipping TUA/STD/PRA.")
            code_prompt = request.refined_prompt
            signature = request.signature or "def solution(*args, **kwargs):"
            edge_cases = request.edge_cases or "Handle all relevant edge cases"
        else:
            logger.info(f"Processing prompt: {request.user_prompt}")

            # Step 1 - TUA
            task_data = {"original_prompt": request.user_prompt, "language": request.language}
            tua_result = generate_structured_prompt(task_data)
            logger.info(f"TUA output: {tua_result}")

            # Step 2 - STD
            std_result = subtask_distributor_agent({
                "structured_prompt": tua_result["structured_prompt"],
                "language": request.language
            })
            logger.info(f"STD output: {std_result}")

            # Step 3 - PRA
            std_for_pra = std_result.get("std_result", std_result)
            refined_prompts_data = PromptRefinerAgent().refine(tua_result, std_for_pra)
            logger.info(f"PRA output: {refined_prompts_data}")

            refined_prompts = refined_prompts_data.get("refined_prompts", [])
            code_prompt = refined_prompts[0]["refined_prompt"] if refined_prompts else (
                f"# Language: {request.language}\n"
                f"# Task: {request.user_prompt}\n"
                f"# Signature: {request.signature or tua_result.get('signature', 'def solution(*args, **kwargs):')}\n"
                f"# Instructions: Write a complete solution. Handle all relevant edge cases."
            )
            signature = request.signature or tua_result.get("signature", "def solution(*args, **kwargs):")
            edge_cases = request.edge_cases or tua_result.get("edge_cases", "Handle all relevant edge cases")

        logger.info(f"Calling solve_problem with: code_prompt={code_prompt[:50]}..., signature={signature}, edge_cases={edge_cases}")
        # Step 4 - Solve Problem
        result = spar.solve_problem(request.user_prompt, code_prompt, signature, edge_cases)
        logger.info(f"Full pipeline result: {result}")
        return result

    except ValueError as ve:
        logger.error(f"Validation error in full pipeline: {str(ve)}", exc_info=True)
        return {"error": "Validation failed", "status": "failed", "details": str(ve)}
    except Exception as e:
        logger.error(f"Error in full pipeline: {str(e)}", exc_info=True)
        return {"error": "Processing failed", "status": "failed", "details": str(e)}

# ---------- Other Endpoints ----------
@app.post("/api/code-generation")
async def run_code_generation(request: PromptRequest):
    try:
        spar = get_spar_system()
        task_data = {"original_prompt": request.user_prompt, "language": request.language}
        tua_result = generate_structured_prompt(task_data)
        signature = tua_result.get("signature", "def solution(*args, **kwargs):")
        code = spar.code_agent.generate_code(request.user_prompt, signature=signature)
        logger.info(f"Generated code: {code}")
        return {"code": code, "status": "success"}
    except Exception as e:
        logger.error(f"Error in code generation: {str(e)}", exc_info=True)
        return {"error": str(e), "status": "failed"}

@app.post("/api/test-generation")
async def run_test_generation(request: dict):
    try:
        spar = get_spar_system()
        problem = request.get("problem", "")
        code = request.get("code", "")
        edge_cases = request.get("edge_cases", "Handle all relevant edge cases")
        constraints = request.get("constraints", "Not specified")
        test_cases = spar.tester.generate_tests(problem, code, edge_cases, constraints)
        logger.info(f"Generated test cases: {test_cases}")
        return {"test_cases": test_cases, "status": "success"}
    except Exception as e:
        logger.error(f"Error in test generation: {str(e)}", exc_info=True)
        return {"error": str(e), "status": "failed"}

@app.post("/api/run-tests")
async def run_tests(request: dict):
    try:
        spar = get_spar_system()
        code = request.get("code", "")
        test_cases = request.get("test_cases", [])
        test_results = spar.tester.run_tests(code, test_cases)
        logger.info(f"Test results: {test_results}")
        return {"test_results": test_results, "status": "success"}
    except Exception as e:
        logger.error(f"Error in running tests: {str(e)}", exc_info=True)
        return {"error": str(e), "status": "failed"}

@app.post("/api/debug-code")
async def debug_code(request: dict):
    try:
        spar = get_spar_system()
        problem = request.get("problem", "")
        code = request.get("code", "")
        error = request.get("error", "")
        test_cases = request.get("test_cases", [])
        debug_result = spar.debugger({
            "problem": problem,
            "code": code,
            "error": error,
            "test_results": {"test_cases": test_cases, "error": error}
        })
        logger.info(f"Debug result: {debug_result}")
        return {"debug_result": debug_result, "status": "success"}
    except Exception as e:
        logger.error(f"Error in debugging code: {str(e)}", exc_info=True)
        return {"error": str(e), "status": "failed"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
