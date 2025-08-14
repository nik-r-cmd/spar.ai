import os
import logging
from jinja2 import Template
from .base_agent import SPARConfig, LocalModelManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """
# Language: {{ language }}
# Signature: {{ signature }}
# Method: {{ method }}
# Edge Cases: {{ edge_cases }}
# Constraints: {{ constraints }}
# Instructions: {{ instructions }}
{% if explanation %}# Explanation: {{ explanation }}{% endif %}
{% if subtask %}# Subtask: {{ subtask }}{% endif %}
"""

class PromptRefinerAgent:
    def __init__(self, config: SPARConfig = None):
        self.config = config or SPARConfig.from_env()
        self.template = Template(PROMPT_TEMPLATE)
        self.model_manager = LocalModelManager()
        self.model_manager.initialize(self.config)

    def _template_prompt(self, tua, std, subtask_desc=None):
        prompt = self.template.render(
            language=tua.get("language", "python"),
            signature=tua.get("signature", "def solution(*args, **kwargs):"),
            method=tua.get("method_used", "general approach"),
            edge_cases=tua.get("edge_cases", "Handle edge cases and invalid inputs appropriately"),
            constraints=tua.get("constraints", "Follow input constraints and performance requirements"),
            instructions=(
                tua.get("instructions", "Write a complete Python function that solves the described problem. "
                "Include handling for all specified edge cases. Do not use input() or print().")
            ),
            explanation=std.get("explanation", ""),
            subtask=subtask_desc
        )
        logger.info(f"Generated base prompt: {prompt}")
        return prompt

    # In prompt_refiner.py, update _llm_polish
    def _llm_polish(self, prompt):
        if not self.model_manager.is_initialized():
            logger.warning("Model not initialized, returning unpolished prompt")
            return prompt
        system_prompt = (
            "You are an expert prompt engineer for code generation. "
            "Given the following structured context, rewrite the prompt to be: "
            "- Clear and unambiguous\n"
            "- Explicit about function signature, input/output, constraints, and edge cases\n"
            "- Concise, but with all necessary details\n"
            "- Ready for a code LLM to generate a robust solution\n"
            "- Do NOT include the actual code implementation or test cases; only describe what the solution should do."
        )
        full_prompt = f"{system_prompt}\n\n{prompt}"
        try:
            polished = self.model_manager.generate_content(full_prompt, max_tokens=512)
            logger.info(f"Polished prompt generated: {polished.strip()}")
            if not polished.strip():
                logger.warning("Polished prompt is empty, using base prompt")
                return prompt
            return polished.strip()
        except Exception as e:
            logger.error(f"Error in LLM polish: {str(e)}")
            return prompt

    def refine(self, tua, std):
        try:
            logger.info(f"TUA input: {tua}")
            logger.info(f"STD input: {std}")

            classification = std.get("classification", "UNKNOWN")
            method_used = tua.get("method_used", "")
            original_prompt = tua.get("original_prompt", "")

            logger.info(f"Classification: {classification}, Method: {method_used}")

            if classification == "UNKNOWN" or not method_used or not original_prompt:
                logger.warning("Falling back to default prompt due to invalid TUA/STD")
                return {
                    "refined_prompts": [{
                        "subtask": "Complete Solution",
                        "refined_prompt": (
                            f"# Language: python\n"
                            f"# Task: {original_prompt or 'Solve the described problem'}\n"
                            f"# Signature: def solution(*args, **kwargs):\n"
                            f"# Instructions: Write a complete Python function to solve the problem as described above. "
                            f"Handle all relevant edge cases. Do not use input() or print()."
                        )
                    }]
                }

            # For SIMPLE or no subtasks, generate a single refined prompt
            if classification == "SIMPLE" or not std.get("subtasks"):
                base_prompt = self._template_prompt(tua, std)
                polished = self._llm_polish(base_prompt)
                return {"refined_prompts": [{"subtask": "Complete Solution", "refined_prompt": polished}]}

            # For COMPLEX: generate prompts for each subtask
            prompts = []
            for i, sub in enumerate(std.get("subtasks", []), 1):
                subtask_desc = sub.get("description", "")
                base_prompt = self._template_prompt(tua, std, subtask_desc)
                polished = self._llm_polish(base_prompt)
                prompts.append({
                    "subtask": f"Step {i}: {subtask_desc}",
                    "refined_prompt": polished
                })
            return {"refined_prompts": prompts}

        except Exception as e:
            logger.error(f"Error in PromptRefinerAgent.refine: {str(e)}")
            return {
                "refined_prompts": [{
                    "subtask": "Complete Solution",
                    "refined_prompt": (
                        f"# Language: python\n"
                        f"# Task: {tua.get('original_prompt', 'Solve the described problem')}\n"
                        f"# Signature: def solution(*args, **kwargs):\n"
                        f"# Instructions: Write a complete Python function to solve the problem as described above. "
                        f"Handle all relevant edge cases. Do not use input() or print()."
                    )
                }]
            }

    def refine_prompt(self, problem: str, code: str, error: str, test_cases: list) -> str:
        """Refine the original problem prompt based on code failure and test cases"""
        refined_prompt = f"""The following code failed to pass the test cases:

Original Problem: {problem}

Failed Code:
{code}

Error: {error}

Test Cases:
{chr(10).join(test_cases)}

Please provide a corrected solution that:
1. Addresses the specific error mentioned above
2. Passes all the provided test cases
3. Maintains the original problem requirements
4. Uses clear, efficient Python code

Corrected solution:"""
        return refined_prompt