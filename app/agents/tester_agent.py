"""
Test generation and execution agent
"""
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
    def generate_tests(self, problem: str, code: str) -> List[str]:
        """Generate test cases for the given code"""
        function_name = self._extract_function_name(code)
        if not function_name:
            logger.warning("Could not extract function name from code")
            return []

        prompt = f"""Generate exactly 5 test cases for this Python function:

Problem: {problem}

Function code:
{code}

Requirements:
- Generate 5 different test assertions
- Use the format: assert {function_name}(input) == expected_output
- Cover edge cases and normal cases
- Make sure all test cases are valid Python assertions
- Return only the assert statements, one per line

Test cases:"""

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

        assert_match = re.search(r'assert\s+\w+\([^)]*\)\s*==\s*[^`\n]+', line)
        if assert_match:
            line = assert_match.group().strip()

        if line.count('"') % 2 != 0:
            line += '"'
        elif line.count("'") % 2 != 0:
            line += "'"

        return line.strip()

    def _is_valid_test_case(self, line: str, function_name: str) -> bool:
        """Check if a line is a valid test case"""
        if not line or not line.startswith('assert') or function_name not in line:
            return False

        if not any(op in line for op in ['==', '!=', '<', '>', '<=', '>=', 'is', 'in']):
            return False

        try:
            ast.parse(line)
            return True
        except SyntaxError:
            return False

    @handle_errors
    def run_tests(self, code: str, test_cases: List[str]) -> Dict[str, Any]:
        """Run test cases against the code"""
        if not test_cases:
            return {"status": "error", "error": "No test cases generated", "passed": 0, "total": 0}

        valid_tests = [test for test in test_cases if self._is_valid_syntax(test)]

        if not valid_tests:
            return {"status": "error", "error": "No valid test cases", "passed": 0, "total": 0}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(f"{code}\n\n")
            f.write("# Test cases\n")
            for test_case in valid_tests:
                f.write(f"{test_case}\n")
            f.write("\nprint('All tests passed!')\n")
            temp_file = f.name

        try:
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=self.config.test_timeout
            )

            if result.returncode == 0:
                return {
                    "status": "pass",
                    "passed": len(valid_tests),
                    "total": len(valid_tests),
                    "test_cases": valid_tests
                }
            else:
                failed_test = self._identify_failed_test(code, result.stderr, test_cases)
                passed_count = self._count_passed_tests(code, valid_tests)
                return {
                    "status": "fail",
                    "error": result.stderr,
                    "passed": passed_count,
                    "total": len(valid_tests),
                    "failed_test": failed_test,
                    "test_cases": valid_tests
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "error": "Test execution timed out",
                "passed": 0,
                "total": len(valid_tests),
                "test_cases": valid_tests
            }
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def _is_valid_syntax(self, test: str) -> bool:
        """Check if test has valid syntax"""
        try:
            ast.parse(test)
            return True
        except SyntaxError:
            return False

    def _identify_failed_test(self, code: str, error: str, test_cases: List[str]) -> str:
        """Extract the specific test that failed from error output"""
        # Simple pattern matching - can be enhanced
        for test in test_cases:
            if test.split('(')[0] in error:  # Match function name
                return test
        return test_cases[0] 

    
    def _count_passed_tests(self, code: str, test_cases: List[str]) -> int:
        """Count how many individual tests pass"""
        passed = 0
        for test_case in test_cases:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(f"{code}\n\n")
                f.write(f"try:\n")
                f.write(f"    {test_case}\n")
                f.write(f"    print('PASS')\n")
                f.write(f"except Exception as e:\n")
                f.write(f"    print(f'FAIL: {{e}}')\n")
                temp_file = f.name

            try:
                result = subprocess.run(
                    ['python', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and 'PASS' in result.stdout:
                    passed += 1
            except subprocess.TimeoutExpired:
                pass
            finally:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
        return passed