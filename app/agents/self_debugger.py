# self_debugger.py
import logging
import re
from typing import Dict, Any, Optional
from .base_agent import LocalModelManager, SPARConfig
import yaml

class SelfDebugger:
    def __init__(self, config: Optional[SPARConfig] = None):
        self.config = config or SPARConfig.from_env()
        self.model_manager = LocalModelManager()
        self.model_manager.initialize(self.config)
        self.logger = logging.getLogger("SelfDebugger")
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.debug_templates = self._load_debug_templates()

    def _load_debug_templates(self) -> Dict[str, str]:
        """Load debug templates from debug_templates.yaml."""
        try:
            with open("app/templates/debug_templates.yaml", "r") as file:
                return yaml.safe_load(file) or {}
        except Exception as e:
            self.logger.error(f"Error loading debug templates: {e}")
            return {}

    def _clean_text(self, text: str) -> str:
        """Clean text by removing escape sequences and formatting properly."""
        if not text:
            return ""
        text = text.replace('\\n', '\n')
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    def _llm_prompt(self, code: str, error: str, test_results: Dict[str, Any]) -> str:
        """Generate a prompt for the LLM to debug the code based on test errors."""
        if not self.model_manager.is_initialized():
            self.logger.error("Model not initialized. Cannot generate LLM response.")
            return "Error: Model not initialized."
        
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are an expert code debugger. Analyze the provided code, error message, and test results, "
                    "then suggest a fix for the error. Use the following approach:\n"
                    "- Identify the root cause of the error.\n"
                    "- If a debug template exists for the error type, apply it.\n"
                    "- Otherwise, propose a logical fix ensuring the function returns a boolean.\n"
                    "- Avoid input() or print() statements.\n"
                    "- Return the fixed code in a code block (```python\n<fixed_code>\n```) and a brief explanation."
                )
            },
            {
                "role": "user",
                "content": (
                    "Debug the following code based on the error and test results:\n\n"
                    "Code:\n```python\n"
                    f"{code}\n"
                    "```\n\n"
                    "Error Message:\n"
                    f"{error}\n\n"
                    "Test Results:\n"
                    f"{test_results}\n\n"
                    "Provide the fixed code with signature def solution(n: int) -> bool and a brief explanation."
                )
            }
        ]
        self.logger.info("Prompting LLM for code debugging...")
        
        try:
            result = self.model_manager.generate_content(prompt)
            self.logger.info("LLM response received.")
            return self._clean_text(result)
        except Exception as e:
            self.logger.error(f"Error in LLM prompt: {e}")
            return f"Error generating response: {str(e)}"

    def _apply_debug_template(self, code: str, error: str) -> Optional[str]:
        """Apply a debug template if available for the error type."""
        error_type = self._extract_error_type(error)
        if error_type in self.debug_templates:
            try:
                template = self.debug_templates[error_type]
                func_match = re.search(r'def\s+(\w+)\s*\((.*?)\):', code)
                if func_match:
                    func_name = func_match.group(1)
                    params = func_match.group(2)
                    param_list = [p.strip() for p in params.split(',') if p.strip()]
                    fixed_code = template.replace('{{func_name}}', func_name)
                    fixed_code = fixed_code.replace('{{params}}', params)
                    fixed_code = fixed_code.replace('{{param_list[0]}}', param_list[0] if param_list else 'n')
                    body_match = re.search(r'def\s+\w+\s*\(.*?\):\s*(.*?)$', code, re.DOTALL)
                    original_body = body_match.group(1) if body_match else ''
                    fixed_code = fixed_code.replace('{{original_body}}', original_body)
                    return fixed_code
            except Exception as e:
                self.logger.error(f"Error applying debug template: {e}")
        return None

    def _extract_error_type(self, error: str) -> str:
        """Extract the error type from the error message."""
        match = re.search(r'(?i)(TypeError|ValueError|TimeoutError|IndexError|KeyError|AttributeError)', error)
        return match.group(1) if match else "UnknownError"

    def __call__(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Debug the code based on test results and errors."""
        try:
            code = input_dict.get("code", "")
            test_results = input_dict.get("test_results", {})
            error = test_results.get("error", "") or input_dict.get("error", "")
            
            if not code or not error:
                raise ValueError("Input must contain 'code' and 'error' or 'test_results' with an error.")
            
            if not self.model_manager.is_initialized():
                self.logger.error("Model not initialized. Returning fallback error.")
                return {
                    "fixed_code": code,
                    "debug_explanation": "Error: Model not initialized.",
                    "success": False
                }
            
            fixed_code = self._apply_debug_template(code, error)
            if fixed_code:
                self.logger.info("Applied debug template successfully.")
                return {
                    "fixed_code": fixed_code,
                    "debug_explanation": f"Applied debug template for {self._extract_error_type(error)}.",
                    "success": True
                }
            
            llm_output = self._llm_prompt(code, error, test_results)
            
            code_match = re.search(r'```python\n(.*?)```', llm_output, re.DOTALL)
            fixed_code = code_match.group(1).strip() if code_match else code
            explanation_match = re.search(r'Explanation:\s*(.*?)(?=\n```|\Z)', llm_output, re.DOTALL)
            debug_explanation = explanation_match.group(1).strip() if explanation_match else self._clean_text(llm_output) or "No explanation provided"
            debug_explanation = self._clean_text(debug_explanation)
            
            return {
                "fixed_code": fixed_code,
                "debug_explanation": debug_explanation,
                "success": bool(code_match)
            }
            
        except Exception as e:
            self.logger.error(f"Error in __call__: {e}")
            return {
                "fixed_code": input_dict.get("code", ""),
                "debug_explanation": f"Error during debugging: {str(e)}",
                "success": False
            }