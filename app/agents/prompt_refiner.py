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
        # For SIMPLE: single prompt
        if not std.get("subtasks"):
            base_prompt = self._template_prompt(tua, std)
            polished = self._llm_polish(base_prompt)
            return {"refined_prompts": [{"subtask": None, "refined_prompt": polished}]}
        # For MEDIUM/COMPLEX: one prompt per subtask
        else:
            prompts = []
            for sub in std["subtasks"]:
                subtask_desc = sub.get("description", "")
                base_prompt = self._template_prompt(tua, std, subtask_desc)
                polished = self._llm_polish(base_prompt)
                prompts.append({
                    "subtask": subtask_desc,
                    "refined_prompt": polished
                })
            return {"refined_prompts": prompts} 