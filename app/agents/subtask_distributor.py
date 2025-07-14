import torch
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
from typing import Dict, List, Union

# Dummy decorator for LangGraph node (replace with actual import in integration)
def langgraph_node(cls):
    return cls

@langgraph_node
class SubtaskDistributor:
    def __init__(self, model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0", device: str = "cuda"):
        self.model_name = model_name
        self.device = device
        self._load_model()

    def _load_model(self):
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if self.device == "cuda" else -1,
            max_new_tokens=64,
            do_sample=False,
        )

    def _is_complex(self, prompt: str) -> bool:
        """Use LLM to classify prompt as simple or complex. Fallback to heuristics if unclear."""
        system_prompt = (
            "Classify the following DSA problem as 'simple' or 'complex'. "
            "A simple problem can be solved in a single function with no input validation or output formatting. "
            "A complex problem requires multiple steps (validation, core logic, formatting). "
            "Respond with only 'simple' or 'complex'.\nProblem: "
        )
        input_text = system_prompt + prompt
        result = self.pipe(input_text)[0]["generated_text"][len(input_text):].strip().lower()
        if "complex" in result:
            return True
        if "simple" in result:
            return False
        # Fallback heuristic: long prompt or keywords
        if len(prompt) > 200 or any(k in prompt.lower() for k in ["validate", "format", "step", "multiple", "return a list", "check if input"]):
            return True
        return False

    def _decompose(self, input_dict: Dict) -> List[Dict]:
        """Decompose the structured prompt into subtasks."""
        base = {k: input_dict.get(k, "") for k in ["language", "method_used", "constraints", "original_prompt"]}
        subtasks = [
            {
                **base,
                "subtask_type": "validation",
                "prompt": f"Write input validation code for: {input_dict['structured_prompt']}"
            },
            {
                **base,
                "subtask_type": "core",
                "prompt": f"Implement the core logic for: {input_dict['structured_prompt']}"
            },
            {
                **base,
                "subtask_type": "format",
                "prompt": f"Format the output as required for: {input_dict['structured_prompt']}"
            },
        ]
        return subtasks

    def __call__(self, input_dict: Dict) -> Union[Dict, List[Dict]]:
        prompt = input_dict.get("structured_prompt", "")
        if not prompt:
            raise ValueError("Input must contain 'structured_prompt'.")
        if self._is_complex(prompt):
            return self._decompose(input_dict)
        # Simple: just forward as is, with subtask_type 'core'
        return {**input_dict, "subtask_type": "core"} 