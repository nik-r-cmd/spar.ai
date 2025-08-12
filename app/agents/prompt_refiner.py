from fastapi import APIRouter
from pydantic import BaseModel
import logging

router = APIRouter()

class PRARequest(BaseModel):
    structured_prompt: str
    subtasks: list = []

@router.post("/pra")
async def prompt_refiner(request: PRARequest):
    try:
        from app.model_manager import global_pipeline
        logging.info("PromptRefiner acquired global pipeline.")

        # Combine structured prompt + subtasks
        full_prompt = f"Refine the following prompt:\n{request.structured_prompt}\n\nSubtasks:\n"
        for sub in request.subtasks:
            full_prompt += f"- {sub}\n"

        response = global_pipeline(full_prompt, max_new_tokens=800, temperature=0.3)
        refined_text = response[0]['generated_text']

        return {"refined_prompts": [{"subtask": "Full Refinement", "refined_prompt": refined_text}]}

    except Exception as e:
        logging.error("PromptRefiner error", exc_info=True)
        return {"error": str(e)}
