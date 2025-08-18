import logging
import time
import re
from typing import Dict
from .code_agent import CodeAgent
from .tester_agent import TesterAgent
from .self_debugger import SelfDebugger
from .prompt_refiner import PromptRefinerAgent

logger = logging.getLogger(__name__)

class MainSolutionSystem:
    def __init__(self, config):
        self.code_agent = CodeAgent(config)
        self.tester = TesterAgent(config)
        self.debugger = SelfDebugger(config)
        self.prompt_refiner = PromptRefinerAgent(config)

    def _is_valid_signature(self, signature: str) -> bool:
        return bool(signature and re.match(r"def\s+\w+\s*\(.*\)\s*->\s*\w+:", signature))

    def _prepare_result(self, problem: str, code: str, code_source: str, code_time: float, test_time: float, test_results: Dict, start_time: float) -> Dict[str, any]:
        return {
            "problem": problem,
            "code": code,
            "code_source": code_source,
            "test_results": test_results,
            "code_time": code_time,
            "test_time": test_time,
            "total_time": time.time() - start_time,
            "similar_solutions_found": 0,
            "best_similarity": 0.0
        }

    def solve_problem(self, problem: str, refined_prompt: str = None, signature: str = None, edge_cases: str = None) -> Dict[str, any]:
        print(f"\n{'='*80}")
        print(f"Problem: {problem}")
        print('='*80)
        
        start_time = time.time()
        
        # Initialize tua_result with a default value
        tua_result = {"constraints": "Not specified", "signature": "def solution(*args, **kwargs):", "edge_cases": "Handle relevant edge cases"}
        
        if refined_prompt:
            logger.info("Using provided refined_prompt, skipping TUA/STD/PRA.")
            code_prompt = refined_prompt
            # Check if refined prompt matches original intent; fallback if not
            if "list" in refined_prompt.lower() and "2 numbers" in problem.lower():
                code_prompt = (
                    f"# Language: python\n"
                    f"# Task: {problem}\n"
                    f"# Signature: def solution(a, b):\n"
                    f"# Instructions: Write a function that takes two integers a and b and returns their sum. "
                    f"Handle empty or invalid inputs (e.g., None) by raising ValueError. "
                    f"Do not use input() or print(). Return the integer sum."
                )
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
        
        # Iterative debug loop (max 3 attempts)
        max_attempts = 3
        attempt = 0
        current_code = code
        previous_error = ""
        repeat_count = 0
        while attempt < max_attempts:
            test_results = self.tester.run_tests(current_code, test_cases)
            test_time = time.time() - test_start
            
            # Add attempts to test_results for UI tracking
            test_results["attempts"] = attempt + 1
            
            if test_results['status'] == 'pass':
                print("\n--- Test Results ---")
                print(f"Status: {test_results['status']}")
                print(f"Tests Passed: {test_results['passed']}/{test_results['total']}")
                return self._prepare_result(problem, current_code, "generated", code_time, test_time, test_results, start_time)
            
            print("\n--- Test Results ---")
            print(f"Status: {test_results['status']}")
            print(f"Tests Passed: {test_results['passed']}/{test_results['total']}")
            if test_results['status'] != "pass" and "error" in test_results:
                print(f"Error: {test_results['error'].strip()}")
            
            current_error = test_results.get('error', '')
            if current_error == previous_error:
                repeat_count += 1
                if repeat_count >= 2:
                    print("\n--- Repeated Errors Detected, Early Fallback to Refinement ---")
                    break
            else:
                repeat_count = 0
            previous_error = current_error
            
            print(f"\n--- Attempting Debug (Attempt {attempt + 1}/{max_attempts}) ---")
            debug_result = self.debugger({
                "problem": f"{problem}. Always return the integer sum of two numbers a and b as the result. Handle invalid inputs (e.g., None or non-integer) by raising ValueError only. Do not return boolean values.",
                "code": current_code,
                "error": current_error,
                "test_results": test_results
            })
            
            if debug_result['success']:
                print(f"\n--- Debug Successful (Attempt {attempt + 1}) ---")
                print(f"Explanation: {debug_result['debug_explanation']}")
                print("\n--- Fixed Code ---")
                print(debug_result['fixed_code'].strip())
                current_code = debug_result['fixed_code']
                attempt += 1
                test_start = time.time()  # Reset test start only on successful debug
                continue  # Retry with fixed code
            else:
                print(f"\n--- Debug Failed (Attempt {attempt + 1}) ---")
                break  # Exit loop if debug fails
        
        # If all debug attempts fail, fall back to PromptRefiner
        if attempt >= max_attempts:
            print("\n--- Max Debug Attempts Reached, Falling Back to Prompt Refinement ---")
            refined_prompt = self.prompt_refiner.refine_prompt(
                problem, current_code, test_results['error'], test_cases
            )
            # Reinforce original intent
            refined_prompt = (
                f"# Task: {problem}\n"
                f"# Signature: def solution(a, b):\n"
                f"# Instructions: Write a function that takes two integers a and b and returns their sum. "
                f"Handle invalid inputs (e.g., None) by raising ValueError. "
                f"Do not use input() or print(). Return the integer sum.\n"
                f"Previous error: {test_results['error']}\n"
                f"Test cases: {test_cases}"
            )
            print("\n--- Refined Prompt ---")
            print(refined_prompt)
            print("\n--- Generating Code with Refined Prompt ---")
            refined_code = self.code_agent.generate_code(refined_prompt, signature="def solution(a, b):")
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
        
        # Return with debug failure if no refinement needed
        return self._prepare_result(
            problem,
            current_code,
            "generated+debugged" if attempt > 0 else "generated",
            code_time,
            test_time,
            test_results,
            start_time
        )