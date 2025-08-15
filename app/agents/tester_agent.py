# tester_agent.py
import os
import ast
import re
import subprocess
import tempfile
import logging
from typing import Dict, List, Optional, Any
from .base_agent import LocalModelManager, handle_errors, SPARConfig

logger = logging.getLogger(__name__)

class TesterAgent:
    """Agent responsible for generating and executing test cases"""
    
    def __init__(self, config: SPARConfig):
        self.config = config
        self.model_manager = LocalModelManager()
        self.model_manager.initialize(config)
        logger.info("TesterAgent initialized")

    @handle_errors
    def generate_tests(self, problem: str, code: str, edge_cases: str = "", constraints: str = "") -> List[str]:
        """Generate test cases for the given code"""
        function_name = self._extract_function_name(code) or "solution"
        if not function_name:
            logger.warning("Using default function name 'solution'")

        prompt = [
            {
                "role": "system",
                "content": (
                    "You are an expert Python test case generator. "
                    "Your job is to create diverse, valid Python test assertions for a given function."
                )
            },
            {
                "role": "user",
                "content": f"""Generate exactly 5 test cases for this Python function:

Problem: {problem or "The problem description is provided above."}

Function code:
{code}

Edge Cases: {edge_cases or "Include edge cases and invalid inputs"}
Constraints: {constraints or "Follow performance and correctness requirements"}

Requirements:
- Generate 5 different test assertions
- Use the format: assert {function_name}(input) == expected_output or assert_raises(Exception, {function_name}, input)
- Cover both normal and edge cases in a real-world manner
- Generate realistic and practical test cases with reasonable input sizes. Avoid extremely large numbers or impractical inputs unless the problem requires it.
- For exception tests, use assert_raises(ExceptionType, function_name, input) without adding '== True' or any comparison
- Ensure all test cases are valid Python assertions and consistent
- Return only the assert statements, one per line

Test cases:"""
            }
        ]

        try:
            response = self.model_manager.generate_content(prompt, max_tokens=256)
            test_cases = self._parse_test_cases(response, function_name)
            if len(test_cases) > 5:
                test_cases = test_cases[:5]
            return test_cases
        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            return []

    def _extract_function_name(self, code: str) -> Optional[str]:
        """Extract function name from code"""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    return node.name
        except SyntaxError:
            pass
        for line in code.split('\n'):
            if line.strip().startswith('def '):
                return line.strip().split('def ')[1].split('(')[0]
        return None

    def _parse_test_cases(self, test_content: str, function_name: str) -> List[str]:
        """Parse test cases from model response"""
        test_cases = []
        lines = test_content.split('\n')

        for line in lines:
            cleaned_line = self._clean_line(line)
            if self._is_valid_test_case(cleaned_line, function_name):
                test_cases.append(cleaned_line)

        unique_tests = []
        seen = set()
        for test in test_cases:
            if test not in seen:
                unique_tests.append(test)
                seen.add(test)

        return unique_tests[:self.config.max_test_cases]

    def _clean_line(self, line: str) -> str:
        """Clean a line to extract a valid assert statement"""
        line = line.strip()
        line = re.sub(r'`+', '', line)
        line = re.sub(r'^\d+\.\s*', '', line)
        line = re.sub(r'^[-*]\s*', '', line)

        assert_match = re.search(r'assert\s+\w+\([^)]*\)\s*(==|raises)\s*[^`\n]+', line)
        if assert_match:
            line = assert_match.group().strip()

        # Remove '== True' from assert_raises lines
        if 'assert_raises' in line:
            line = re.sub(r'\s*==\s*True\s*$', '', line)

        if line.count('"') % 2 != 0:
            line += '"'
        elif line.count("'") % 2 != 0:
            line += "'"

        return line.strip()

    def _is_valid_test_case(self, line: str, function_name: str) -> bool:
        """Check if a line is a valid test case"""
        if not line or not line.startswith('assert') or function_name not in line:
            return False
        if not any(op in line for op in ['==', '!=', '<', '>', '<=', '>=', 'is', 'in', 'raises']):
            return False
        try:
            ast.parse(line)
            return True
        except SyntaxError:
            return False

    @handle_errors
    def run_tests(self, code: str, test_cases: List[str]) -> Dict[str, Any]:
        """Run test cases against the code, individually for detailed results"""
        if not test_cases:
            return {"status": "error", "error": "No test cases generated", "passed": 0, "total": 0, "detailed_test_results": []}

        valid_tests = [test for test in test_cases if self._is_valid_syntax(test)]
        if not valid_tests:
            return {"status": "error", "error": "No valid test cases", "passed": 0, "total": 0, "detailed_test_results": []}

        detailed_results = []
        passed = 0
        total = len(valid_tests)

        for test_case in valid_tests:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code + "\n\n")
                if 'assert_raises' in test_case:
                    match = re.search(r'assert_raises\((.+?),\s*(.+?),\s*(.+?)\)', test_case)
                    if match:
                        exception = match.group(1).strip()
                        func = match.group(2).strip()
                        args = match.group(3).strip()
                        f.write(f"try:\n    {func}({args})\nexcept {exception} as e:\n    print('PASS')\nelse:\n    print('FAIL: No exception raised')\n")
                    else:
                        f.write(f"print('FAIL: Invalid assert_raises format')\n")
                else:
                    f.write(f"try:\n    {test_case}\n    print('PASS')\nexcept Exception as e:\n    print(f'FAIL: {{e}}')\n")
                temp_file = f.name

            try:
                result = subprocess.run(
                    ['python', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=self.config.test_timeout
                )
                output = result.stdout.strip()
                if 'PASS' in output:
                    detailed_results.append({"test": test_case, "status": "pass"})
                    passed += 1
                else:
                    error_msg = output.replace('FAIL: ', '') if 'FAIL' in output else result.stderr
                    detailed_results.append({"test": test_case, "status": "fail", "error": error_msg})
            except subprocess.TimeoutExpired:
                detailed_results.append({"test": test_case, "status": "fail", "error": "Timeout"})
            finally:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

        status = "pass" if passed == total else "fail"
        overall_error = "All tests passed" if status == "pass" else "Some tests failed"

        return {
            "status": status,
            "passed": passed,
            "total": total,
            "error": overall_error,
            "test_cases": valid_tests,
            "detailed_test_results": detailed_results
        }

    def _is_valid_syntax(self, test: str) -> bool:
        """Check if test has valid syntax"""
        try:
            ast.parse(test)
            return True
        except SyntaxError:
            return False