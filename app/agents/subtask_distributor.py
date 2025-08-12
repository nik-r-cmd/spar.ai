# app/agents/subtask_distributor.py
import re
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from app.model_manager import global_pipeline

logger = logging.getLogger("SubtaskDistributor")
if not logger.hasHandlers():
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s'))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

router = APIRouter()

class STDRequest(BaseModel):
    structured_prompt: str
    language: str = "python"

class STDResponse(BaseModel):
    llm_response: str
    classification: str
    explanation: Optional[str] = None
    subtasks: Optional[List[Dict[str, str]]] = None

class SubtaskDistributor:
    def __init__(self, pipeline):
        self.pipe = pipeline
        self.logger = logger

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.replace('\\n', '\n')
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    def _llm_prompt(self, structured_prompt: str) -> str:
        if self.pipe is None:
            self.logger.error("LLM pipe not available.")
            return "Error: LLM pipe is not available."
        full_prompt = (
            "You are an expert DSA problem classifier and decomposer.\n\n"
            "Classify the following problem as SIMPLE, MEDIUM, or COMPLEX.\n"
            "Respond exactly in the format:\n"
            "Classification: <SIMPLE/MEDIUM/COMPLEX>\n"
            "Explanation: <brief reasoning>\n"
            "If COMPLEX or MEDIUM, include:\n"
            "Subtasks:\n"
            "Step 1: <description>\n"
            "Step 2: <description>\n\n"
            "DSA Problem:\n"
            f"{structured_prompt}\n"
        )
        self.logger.info("Prompting LLM for classification and decomposition...")
        try:
            outputs = self.pipe(full_prompt, max_new_tokens=512, do_sample=True, temperature=0.3)
            if isinstance(outputs, list) and len(outputs) > 0 and "generated_text" in outputs[0]:
                generated = outputs[0]["generated_text"]
            elif isinstance(outputs, dict) and "generated_text" in outputs:
                generated = outputs["generated_text"]
            elif isinstance(outputs, str):
                generated = outputs
            else:
                generated = str(outputs)
            self.logger.info("LLM response received.")
            return self._clean_text(generated)
        except Exception as e:
            self.logger.exception("Error in LLM prompt")
            return f"Error generating response: {str(e)}"

    def __call__(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        try:
            structured_prompt = input_dict.get("structured_prompt", "")
            if not structured_prompt:
                raise ValueError("Input must contain 'structured_prompt'.")
            llm_output = self._llm_prompt(structured_prompt)
            classification = "UNKNOWN"
            explanation = ""
            subtasks = []

            class_match = re.search(r"Classification:\s*(SIMPLE|MEDIUM|COMPLEX)", llm_output, re.IGNORECASE)
            if class_match:
                classification = class_match.group(1).upper()

            explanation_match = re.search(r"Explanation:\s*(.*?)(?=\nSubtasks:|\Z)", llm_output, re.DOTALL | re.IGNORECASE)
            if explanation_match:
                explanation = explanation_match.group(1).strip()

            if "Subtasks:" in llm_output or re.search(r"Step\s+\d+:", llm_output, re.IGNORECASE):
                step_pattern = re.compile(r"Step\s+(\d+):\s*(.*?)(?=\nStep\s+\d+:|\Z)", re.DOTALL | re.IGNORECASE)
                matches = step_pattern.findall(llm_output)
                for idx, desc in matches:
                    subtasks.append({"step": f"Step {idx}", "description": self._clean_text(desc)})

            return {
                "llm_response": llm_output,
                "classification": classification,
                "explanation": explanation,
                "subtasks": subtasks if subtasks else None
            }

        except Exception as e:
            self.logger.exception("Error in SubtaskDistributor __call__")
            return {
                "llm_response": f"Error: {str(e)}",
                "classification": "ERROR",
                "explanation": str(e),
                "subtasks": None
            }

# singleton agent using shared pipeline
agent = SubtaskDistributor(global_pipeline)

def run_subtask_distributor(structured_prompt: str):
    return agent({"structured_prompt": structured_prompt})

@router.post("/std", response_model=STDResponse)
async def std_endpoint(req: STDRequest):
    try:
        input_dict = {"structured_prompt": req.structured_prompt, "language": req.language}
        result = agent(input_dict)
        return {
            "llm_response": result.get("llm_response", ""),
            "classification": result.get("classification", "UNKNOWN"),
            "explanation": result.get("explanation", ""),
            "subtasks": result.get("subtasks", None)
        }
    except Exception as e:
        logger.exception("STD endpoint error")
        raise HTTPException(status_code=500, detail=str(e))
