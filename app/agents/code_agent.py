import re
import ast
import logging
from typing import Optional
from .base_agent import LocalModelManager, handle_errors, SPARConfig

logger = logging.getLogger(__name__)

class CodeAgent:
    """Agent responsible for generating Python code solutions"""
    
    def __init__(self, config: SPARConfig):
        self.config = config
        self.model_manager = LocalModelManager()
        self.model_manager.initialize(config)
        logger.info("CodeAgent initialized")

    @handle_errors
    def generate_code(self, problem: str, signature: Optional[str] = None) -> str:
        """Generate code solution for the given problem"""
        # Use provided signature or default one
        if not signature:
            signature = "def solution(*args, **kwargs):\n    pass"

        prompt = [
            {
                "role": "system",
                "content": (
                    "You are an expert Python programmer. Generate a function that solves the given problem. "
                    "Follow the exact function signature provided. "
                    "Do not use input() or print() statements. "
                    "Include error handling for invalid inputs when appropriate. "
                    "Return only the Python function code inside a code block."
                )
            },
            {
                "role": "user",
                "content": f"""Solve this problem:

{problem}

Requirements:
- Use the exact function signature: {signature.splitlines()[0]}
- Handle edge cases where applicable
- Do not use input() or print()
- Include error handling with appropriate exceptions
- Return only the function code in a code block

Example format:
```python
{signature}
    # your code here
```"""
            }
        ]

        try:
            response = self.model_manager.generate_content(prompt)
            code = self._extract_code_from_response(response)
            if not code:
                logger.warning("No valid code extracted from response")
                return ""
            return code
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return ""

    def _extract_code_from_response(self, response: str) -> str:
        """Extract Python code from model response and validate it"""
        # Try matching fenced code block first
        match = re.search(r'```(?:python)?\s*\n(.*?)```', response, re.DOTALL | re.IGNORECASE)
        if match:
            code = match.group(1).strip()
            if self._is_valid_code(code):
                return code
        
        # Fallback: try grabbing function definition manually
        lines = response.splitlines()
        code_lines = []
        in_function = False
        
        for line in lines:
            if line.strip().startswith('def '):
                in_function = True
                code_lines.append(line)
            elif in_function:
                if line.strip() and not (line.startswith(' ') or line.startswith('\t')):
                    break
                code_lines.append(line)
        
        code = "\n".join(code_lines).strip()
        if code and self._is_valid_code(code):
            return code
        
        logger.warning("No valid Python function found in response")
        return ""

    def _is_valid_code(self, code: str) -> bool:
        """Validate if the code is a syntactically correct Python function"""
        try:
            parsed = ast.parse(code)
            return any(isinstance(node, ast.FunctionDef) for node in parsed.body)
        except SyntaxError:
            return False
