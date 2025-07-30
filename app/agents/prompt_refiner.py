import os
from jinja2 import Template
from transformers import pipeline

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
    def __init__(self, llm_pipe=None):
        self.template = Template(PROMPT_TEMPLATE)
        self.llm_pipe = llm_pipe  # Should be a HuggingFace pipeline or similar

    def _template_prompt(self, tua, std, subtask_desc=None):
        return self.template.render(
            language=tua.get("language", ""),
            signature=tua.get("signature", ""),
            method=tua.get("method_used", ""),
            edge_cases=tua.get("edge_cases", ""),
            constraints=tua.get("constraints", ""),
            instructions=tua.get("instructions", ""),
            explanation=std.get("explanation", ""),
            subtask=subtask_desc
        )

    def _llm_polish(self, prompt):
        if self.llm_pipe is None:
            return prompt
        system_prompt = (
            "You are an expert prompt engineer for code generation. "
            "Given the following structured context and subtask, rewrite the prompt to be: "
            "- Clear and unambiguous\n"
            "- Explicit about function signature, input/output, constraints, and edge cases\n"
            "- Concise, but with all necessary details\n"
            "- Ready for a code LLM to generate a robust solution\n"
            "If possible, add a relevant example or clarify any vague requirements."
        )
        full_prompt = f"{system_prompt}\n\n{prompt}"
        outputs = self.llm_pipe(full_prompt, max_new_tokens=512)
        if isinstance(outputs, list) and len(outputs) > 0:
            return outputs[0]["generated_text"] if "generated_text" in outputs[0] else outputs[0]
        return str(outputs)

    def refine(self, tua, std):
        # For SIMPLE: single comprehensive prompt
        subtasks = std.get("subtasks", [])
        if not subtasks or len(subtasks) == 0:
            base_prompt = self._template_prompt(tua, std)
            polished = self._llm_polish(base_prompt)
            # Return a clean, focused prompt for simple problems
            return {"refined_prompts": [{"subtask": "Complete Solution", "refined_prompt": polished}]}
        # For MEDIUM/COMPLEX: focused prompts for each subtask
        else:
            prompts = []
            for i, sub in enumerate(subtasks, 1):
                subtask_desc = sub.get("description", "")
                base_prompt = self._template_prompt(tua, std, subtask_desc)
                polished = self._llm_polish(base_prompt)
                # Create focused prompts that can be passed to code agent
                prompts.append({
                    "subtask": f"Step {i}: {subtask_desc}",
                    "refined_prompt": polished
                })
            return {"refined_prompts": prompts} 