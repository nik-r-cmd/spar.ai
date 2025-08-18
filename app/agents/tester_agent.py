import logging
import subprocess
import tempfile
import os
from typing import List, Dict, Any
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class TesterAgent(BaseAgent):
    def __init__(self, config):
        super().__init__(config)
        self.config = config

    def generate_tests(self, problem: str, code: str, edge_cases: str, constraints: str) -> List[str]:
        prompt = (
            f"""Generate exactly 5 test cases for this Python function:\n\n"
            f"Problem: {problem or 'The problem description is provided above.'}\n\n"
            f"Function code:\n{code}\n\n"
            f"Edge Cases: {edge_cases or 'Include edge cases like None or non-integer inputs'}\n"
            f"Constraints: {constraints or 'Follow performance and correctness requirements'}\n\n"
            f"Requirements:\n"
            f"- Generate 5 different test assertions\n"
            f"- Use the format: assert solution(a, b) == expected_output or assert_raises(ValueError, solution, a, b) for exception cases\n"
            f"- Cover both normal and edge cases\n"
            f"- Ensure all test cases are valid Python assertions\n"
            f"- Return only the assert statements, one per line\n\n"
            f"Test cases:"""
        )
        response = self.generate_content(prompt)  # Use inherited generate_content
        test_cases = [line.strip() for line in response.split("\n") if line.strip() and line.strip().startswith("assert")]
        return test_cases[:5]  # Ensure exactly 5 tests

    @staticmethod
    def _is_valid_syntax(test_case: str) -> bool:
        try:
            compile(test_case, "<string>", "exec")
            return True
        except SyntaxError:
            return False

    def run_tests(self, code: str, test_cases: List[str]) -> Dict[str, Any]:
        if not test_cases:
            return {"status": "error", "error": "No test cases generated", "passed": 0, "total": 0, "detailed_test_results": [], "test_cases": []}

        valid_tests = [test for test in test_cases if self._is_valid_syntax(test)]
        if not valid_tests:
            return {"status": "error", "error": "No valid test cases", "passed": 0, "total": 0, "detailed_test_results": [], "test_cases": []}

        detailed_results = []
        passed = 0

        for test_case in valid_tests:
            status = "fail"
            error = ""
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code + "\n")
                f.write("try:\n")
                if 'assert_raises' in test_case:
                    expected_exc = test_case.split('assert_raises(')[1].split(',')[0].strip()
                    args = test_case.split('assert_raises(')[1].split(')')[0].split(',')[1:]
                    f.write(f"    {test_case.split('assert_raises')[0]}assert_raises({expected_exc}, lambda: solution{''.join(args)})\n")
                else:
                    f.write(f"    {test_case}\n")
                f.write("except AssertionError as ae:\n")
                f.write("    print(f'ASSERTION_FAILED: {ae}')\n")
                f.write("except Exception as e:\n")
                f.write("    print(f'ERROR: {type(e).__name__}: {str(e)}')\n")
                f.write("else:\n")
                f.write("    print('PASS')\n")
                temp_file = f.name

            try:
                result = subprocess.run(
                    ['python', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=self.config.test_timeout
                )
                output = result.stdout + result.stderr
                if 'PASS' in output:
                    status = "pass"
                    passed += 1
                elif 'ASSERTION_FAILED' in output:
                    status = "fail"
                    error = output.split('ASSERTION_FAILED: ')[1].strip() if 'ASSERTION_FAILED: ' in output else "Assertion failed"
                elif 'ERROR' in output:
                    status = "error"
                    error = output.split('ERROR: ')[1].strip() if 'ERROR: ' in output else "Unknown error"

            except subprocess.TimeoutExpired:
                status = "timeout"
                error = "Test execution timed out"
            finally:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
        
            detailed_results.append({
                "test": test_case,
                "status": status,
                "error": "No error" if not error else error
            })

        overall_status = "pass" if passed == len(valid_tests) else "fail"
        overall_error = "All tests passed" if overall_status == "pass" else "\n".join([r["error"] for r in detailed_results if r["error"] != "No error"])

        return {
            "status": overall_status,
            "error": overall_error,
            "passed": passed,
            "total": len(valid_tests),
            "test_cases": valid_tests,
            "detailed_test_results": detailed_results,
            "attempts": 1
        }