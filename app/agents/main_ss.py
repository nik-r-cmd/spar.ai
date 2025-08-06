"""
Main SPAR System
"""
import time
from typing import Optional, Dict, Any, List
from .base_agent import SPARConfig, handle_errors
from .code_agent import CodeAgent
from .tester_agent import TesterAgent
from .prompt_refiner import PromptRefinerAgent

import logging
logging.basicConfig(level=logging.INFO)

class SPARSystem:
    def __init__(self, config: Optional[SPARConfig] = None):
        self.config = config or SPARConfig.from_env()
        print("Initializing SPAR System")

        self.code_agent = CodeAgent(self.config)
        self.tester = TesterAgent(self.config)
        self.debugger = SelfDebugger(self.config, self.tester)
        self.prompt_refiner = PromptRefinerAgent(self.config)

        print("SPAR System ready")

    def solve_problem(self, problem: str, refined_prompt: str = None) -> Dict[str, Any]:
        """Solve problem with debugging capabilities"""
        print(f"\n{'='*80}")
        print(f"Problem: {problem}")
        print('='*80)
    
        start_time = time.time()
    
        # Generate code directly (no vector store lookup)
        print("\n--- Code Generation ---")
        print("Code Source: Generated")
        
        generation_start = time.time()
        
        # Use refined prompt if provided, otherwise use original problem
        code_prompt = refined_prompt if refined_prompt else problem
        code = self.code_agent.generate_code(code_prompt)
        code_time = time.time() - generation_start
    
        if not code.strip():
            print("No valid code generated")
            test_results = {"status": "error", "error": "No valid code generated", "passed": 0, "total": 0}
            return {
                "problem": problem,
                "code": code,
                "code_source": "generated",
                "test_results": test_results,
                "code_time": code_time,
                "test_time": 0,
                "total_time": time.time() - start_time,
                "similar_solutions_found": 0,
                "best_similarity": 0.0
            }
    
        print("\n--- Generated Code ---")
        print(code.strip())
    
        print("\n--- Generated Test Cases ---")
        test_start = time.time()
        test_cases = self.tester.generate_tests(problem, code)
        for i, test in enumerate(test_cases, 1):
            print(f"{i}. {test}")
    
        if not test_cases:
            print("\n--- Test Generation Failed ---")
            test_results = {"status": "error", "error": "No tests generated", "passed": 0, "total": 0}
            return {
                "problem": problem,
                "code": code,
                "code_source": "generated",
                "test_results": test_results,
                "code_time": code_time,
                "test_time": 0,
                "total_time": time.time() - start_time,
                "similar_solutions_found": 0,
                "best_similarity": 0.0
            }
    
        # Run initial tests
        test_results = self.tester.run_tests(code, test_cases)
        test_time = time.time() - test_start
    
        # If tests pass, return success
        if test_results['status'] == 'pass':
            print("\n--- Initial Test Results ---")
            print(f"Status: {test_results['status']}")
            print(f"Tests Passed: {test_results['passed']}/{test_results['total']}")
            return self._prepare_result(problem, code, "generated", code_time, test_time,
                                       test_results, start_time)
    
        # If tests fail, attempt to debug
        print("\n--- Initial Test Results ---")
        print(f"Status: {test_results['status']}")
        print(f"Tests Passed: {test_results['passed']}/{test_results['total']}")
        if test_results['status'] != "pass" and "error" in test_results:
            print(f"Error: {test_results['error'].strip()}")
    
        print("\n--- Attempting Debug ---")
        debug_result = self.debugger.debug_and_fix(
            problem, code, test_results['error'], test_cases
        )
    
        if debug_result['fix_successful']:
            print("\n--- Debug Successful ---")
            print(f"Fix Type: {debug_result['fix_type']}")
            print(f"Explanation: {debug_result['fix_explanation']}")
            print("\n--- Fixed Code ---")
            print(debug_result['fixed_code'].strip())
    
            return self._prepare_result(
                problem,
                debug_result['fixed_code'],
                "generated+fixed",
                code_time,
                time.time() - test_start,
                debug_result['test_results'],
                start_time
            )
        else:
            print("\n--- Debug Failed ---")
            print("Passing to PromptRefinerAgent...")
    
            # If debug fails, pass to prompt refiner
            refined_prompt = self.prompt_refiner.refine_prompt(
                problem, code, test_results['error'], test_cases
            )
    
            print(f"\n--- Refined Prompt ---")
            print(refined_prompt)
    
            # Generate new code with refined prompt
            print("\n--- Generating Code with Refined Prompt ---")
            refined_code = self.code_agent.generate_code(refined_prompt)
            refined_test_cases = self.tester.generate_tests(problem, refined_code)
            refined_test_results = self.tester.run_tests(refined_code, refined_test_cases)
    
            return self._prepare_result(
                problem,
                refined_code,
                "generated+refined",
                code_time + (time.time() - test_start),
                time.time() - test_start,
                refined_test_results,
                start_time
            )

    def _prepare_result(self, problem: str, code: str, code_source: str,
                       code_time: float, test_time: float, test_results: Dict,
                       start_time: float) -> Dict:
        """Prepare the result dictionary"""
        total_time = time.time() - start_time

        print("\n--- Final Test Results ---")
        print(f"Status: {'PASS' if test_results['status'] == 'pass' else 'FAIL'} {test_results['status']}")
        print(f"Tests Passed: {test_results['passed']}/{test_results['total']}")

        print("\n--- Timing Summary ---")
        print(f"Code Generation Time: {code_time:.2f}s")
        print(f"Test/Debug Time: {test_time:.2f}s")
        print(f"Total Time: {total_time:.2f}s")

        return {
            "problem": problem,
            "code": code,
            "code_source": code_source,
            "test_results": test_results,
            "code_time": code_time,
            "test_time": test_time,
            "total_time": total_time,
            "similar_solutions_found": 0,
            "best_similarity": 0.0
        }

# Example usage
if __name__ == "__main__":
    # Initialize the system
    spar = SPARSystem()
    
    # Test with a simple problem
    result = spar.solve_problem("Write a function to calculate factorial of a number")
    print(f"\nFinal Result: {result}")