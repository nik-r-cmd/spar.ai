# app/agents/code_agent.py
import logging
from typing import Dict, Any
from app.agents.base_agent import LocalModelManager, handle_errors

LOGGER = logging.getLogger("CodeAgent")
if not LOGGER.hasHandlers():
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s'))
    LOGGER.addHandler(h)
LOGGER.setLevel(logging.INFO)


class CodeAgent:
    def __init__(self):
        try:
            self.pipe = LocalModelManager.get_pipeline()
            LOGGER.info("CodeAgent connected to global pipeline.")
        except Exception as e:
            LOGGER.error("Failed to get pipeline for CodeAgent: %s", e)
            self.pipe = None

    @handle_errors(default_return={"error": "code generation failed"})
    def generate_code(self, refined_prompt: str, max_new_tokens: int = 512) -> Dict[str, Any]:
        if self.pipe is None:
            raise RuntimeError("LLM pipeline not available for code generation")
        LOGGER.info("CodeAgent generating code from prompt (len=%d)", len(refined_prompt))
        outputs = self.pipe(refined_prompt, max_new_tokens=max_new_tokens, do_sample=False)
        # try to extract generated_text
        if isinstance(outputs, list) and len(outputs) > 0 and isinstance(outputs[0], dict) and "generated_text" in outputs[0]:
            return {"generated_code": outputs[0]["generated_text"]}
        if isinstance(outputs, dict) and "generated_text" in outputs:
            return {"generated_code": outputs["generated_text"]}
        return {"generated_code": str(outputs)}


# If other modules expect LocalModelManager, CodeAgent, etc. they can import these names
LocalModelManager = LocalModelManager
