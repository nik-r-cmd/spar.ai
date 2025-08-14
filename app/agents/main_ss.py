import time
from typing import Optional, Dict, Any, List
from .base_agent import SPARConfig, handle_errors
from .code_agent import CodeAgent
from .tester_agent import TesterAgent
from .prompt_refiner import PromptRefinerAgent
from .self_debugger import SelfDebugger

import logging
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

class SPARSystem:
    def __init__(self, config: Optional[SPARConfig] = None):
        self.config = config or SPARConfig.from_env()
        print("Initializing SPAR System")
        self.code_agent = CodeAgent(self.config)
        self.tester = TesterAgent(self.config)
        self.debugger = SelfDebugger(self.config)
        self.prompt_refiner = PromptRefinerAgent(self.config)
        print("SPAR System ready")

    # In main_ss.py, update solve_problem
    def solve_problem(self, problem: str, refined_prompt: str = None, signature: str = None, edge_cases: str = None) -> Dict[str, Any]:
        print(f"\n{'='*80}")
        print(f"Problem: {problem}")
        print('='*80)
    
        start_time = time.time()
    
        if refined_prompt:
            logger.info("Using provided refined_prompt, skipping TUA/STD/PRA.")
            code_prompt = refined_prompt
            tua_result = {"signature": signature or "def solution(*args, **kwargs):", "edge_cases": edge_cases or "Handle relevant edge cases"}
        else:
            logger.info(f"Prompt received by TUA: {problem}")
            from .task_understanding_agent import generate_structured_prompt
            tua_result = generate_structured_prompt({"original_prompt": problem, "language": "python"})
            from .subtask_distributor import run_subtask_distributor
            std_result = run_subtask_distributor(tua_result["structured_prompt"])
            refined_prompts = self.prompt_refiner.refine(tua_result, std_result)["refined_prompts"]
            if not refined_prompts or not refined_prompts[0]["refined_prompt"].strip():
                logger.error("No valid refined prompt generated, falling back to default")
                fallback_sig = signature or tua_result.get("signature", "def solution(*args, **kwargs):")
                code_prompt = (
                    f"# Language: python\n"
                    f"# Task: {problem}\n"
                    f"# Signature: {fallback_sig}\n"
                    f"# Instructions: Solve the above task in Python using the given signature. "
                    f"Handle relevant edge cases for this task. "
                    f"Do not use input() or print(). Return the result from the function."
                )
            else:
                code_prompt = refined_prompts[0]["refined_prompt"]
    
        # Validate and set signature
        signature = signature or tua_result.get("signature", "def solution(*args, **kwargs):")
        if not signature or not re.match(r"def\s+\w+\s*\(.*\)\s*->\s*\w+:", signature):
            logger.error(f"Invalid signature detected: {signature}, falling back to default")
            signature = "def solution(*args, **kwargs):"
        edge_cases = edge_cases or tua_result.get("edge_cases", "Handle relevant edge cases")
    
        logger.info(f"Code prompt: {code_prompt}")
        logger.info(f"Signature: {signature}")
        logger.info(f"Edge cases: {edge_cases}")
    
        print("\n--- Code Generation ---")
        print("Code Source: Generated")
    
        generation_start = time.time()
        try:
            code = self.code_agent.generate_code(code_prompt, signature=signature)
            logger.info(f"Generated code: {code}")
        except Exception as e:
            logger.error(f"Error in code generation: {str(e)}")
            code = f"# Fallback: Error generating code - {str(e)}\npass"
        code_time = time.time() - generation_start
    
        if not code.strip():
            logger.error("No valid code generated")
            print("No valid code generated")
            test_results = {"status": "error", "error": "No valid code generated", "passed": 0, "total": 0}
            return self._prepare_result(problem, code, "generated", code_time, 0, test_results, start_time)
    
        print("\n--- Generated Code ---")
        print(code.strip())
    
        print("\n--- Generated Test Cases ---")
        test_start = time.time()
        test_cases = self.tester.generate_tests(problem, code, edge_cases, tua_result.get("constraints", "Not specified"))
        for i, test in enumerate(test_cases, 1):
            print(f"{i}. {test}")
    
        if not test_cases:
            print("\n--- Test Generation Failed ---")
            test_results = {"status": "error", "error": "No tests generated", "passed": 0, "total": 0}
            return self._prepare_result(problem, code, "generated", code_time, 0, test_results, start_time)
    
        test_results = self.tester.run_tests(code, test_cases)
        test_time = time.time() - test_start
    
        if test_results['status'] == 'pass':
            print("\n--- Initial Test Results ---")
            print(f"Status: {test_results['status']}")
            print(f"Tests Passed: {test_results['passed']}/{test_results['total']}")
            return self._prepare_result(problem, code, "generated", code_time, test_time, test_results, start_time)
    
        print("\n--- Initial Test Results ---")
        print(f"Status: {test_results['status']}")
        print(f"Tests Passed: {test_results['passed']}/{test_results['total']}")
        if test_results['status'] != "pass" and "error" in test_results:
            print(f"Error: {test_results['error'].strip()}")
    
        print("\n--- Attempting Debug ---")
        debug_result = self.debugger({
            "problem": problem,
            "code": code,
            "error": test_results.get('error', ''),
            "test_results": test_results
        })
    
        if debug_result['success']:
            print("\n--- Debug Successful ---")
            print(f"Explanation: {debug_result['debug_explanation']}")
            print("\n--- Fixed Code ---")
            print(debug_result['fixed_code'].strip())
    
            return self._prepare_result(
                problem,
                debug_result['fixed_code'],
                "generated+fixed",
                code_time,
                time.time() - test_start,
                test_results,
                start_time
            )
        else:
            print("\n--- Debug Failed ---")
            print("Passing to PromptRefinerAgent...")
    
            refined_prompt = self.prompt_refiner.refine_prompt(
                problem, code, test_results['error'], test_cases
            )
    
            print("\n--- Refined Prompt ---")
            print(refined_prompt)
    
            print("\n--- Generating Code with Refined Prompt ---")
            refined_code = self.code_agent.generate_code(refined_prompt, signature=signature)
            refined_test_cases = self.tester.generate_tests(problem, refined_code, edge_cases, tua_result.get("constraints", "Not specified"))
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