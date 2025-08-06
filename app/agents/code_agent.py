"""
Code generation agent
"""
import re
import logging
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
    def generate_code(self, problem: str) -> str:
        """Generate code solution for the given problem"""
        prompt = f"""You are an expert Python programmer. Solve this problem:

{problem}

Requirements:
- Write clean, efficient Python code
- Provide only the function definition
- Include proper error handling if needed
- Use descriptive variable names
- Return only the Python function code, no explanations

Python function:"""

        try:
            response = self.model_manager.generate_content(prompt)
            code = self._extract_code_from_response(response)
            return code
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            return ""

    def _extract_code_from_response(self, response: str) -> str:
        """Extract Python code from model response"""
        if "```python" in response:
            match = re.search(r'```python\s*\n(.*?)```', response, re.DOTALL)
            if match:
                return match.group(1).strip()
        elif "```" in response:
            match = re.search(r'```\s*\n(.*?)```', response, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        lines = response.split('\n')
        code_lines = []
        in_function = False
        
        for line in lines:
            if line.strip().startswith('def '):
                in_function = True
                code_lines.append(line)
            elif in_function:
                if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                    break
                code_lines.append(line)
        
        if code_lines:
            return '\n'.join(code_lines)
        
        return response.strip()