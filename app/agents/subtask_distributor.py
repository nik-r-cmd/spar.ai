import re
from typing import Dict, List, Union

class SubtaskDistributor:
    def __init__(self, llm_classifier=None):
        """
        llm_classifier: Callable that takes a prompt and returns 'simple' or 'complex'.
        """
        self.llm_classifier = llm_classifier

    def parse_structured_prompt(self, structured_prompt: str) -> Dict:
        """
        Extracts fields from the structured prompt string.
        """
        fields = {
            "task": "",
            "signature": "",
            "method": "",
            "edge_cases": "",
            "constraints": "",
            "instructions": "",
            "test_cases": ""
        }
        for line in structured_prompt.splitlines():
            if line.startswith("# Task:"):
                fields["task"] = line[len("# Task:"):].strip()
            elif line.startswith("# Signature:"):
                fields["signature"] = line[len("# Signature:"):].strip()
            elif line.startswith("# Method:"):
                fields["method"] = line[len("# Method:"):].strip()
            elif line.startswith("# Edge Cases:"):
                fields["edge_cases"] = line[len("# Edge Cases:"):].strip()
            elif line.startswith("# Constraints:"):
                fields["constraints"] = line[len("# Constraints:"):].strip()
            elif line.startswith("# Instructions:"):
                fields["instructions"] = line[len("# Instructions:"):].strip()
            elif line.startswith("# Test Cases:"):
                fields["test_cases"] = line[len("# Test Cases:"):].strip()
        return fields

    def is_complex_prompt(self, structured_prompt: str) -> bool:
        """
        Heuristic + LLM fallback for classifying prompt complexity.
        """
        # Heuristic
        if "edge case" in structured_prompt.lower() or \
           "validate" in structured_prompt.lower() or \
           "format" in structured_prompt.lower() or \
           len(structured_prompt.split()) > 150:
            return True
        # Fallback to LLM if available
        if self.llm_classifier:
            result = self.llm_classifier(structured_prompt)
            return result.strip().lower() == "complex"
        return False

    def generate_subtasks(self, parsed: Dict, original_context: str, language: str) -> List[Dict]:
        """
        Generate subtasks for complex tasks.
        """
        subtasks = [
            {
                "subtask_type": "input_validation",
                "original_context": original_context,
                "signature": parsed["signature"],
                "instructions": f"Write input validation code. {parsed['instructions']}",
                "language": language
            },
            {
                "subtask_type": "core_algorithm",
                "original_context": original_context,
                "signature": parsed["signature"],
                "instructions": f"Implement the core algorithm. {parsed['instructions']}",
                "language": language
            },
            {
                "subtask_type": "output_formatting",
                "original_context": original_context,
                "signature": parsed["signature"],
                "instructions": f"Format the output as required. {parsed['instructions']}",
                "language": language
            }
        ]
        return subtasks

    def __call__(self, input_dict: Dict) -> Union[Dict, List[Dict]]:
        """
        Main entry: parses, classifies, and routes tasks/subtasks.
        """
        structured_prompt = input_dict["structured_prompt"]
        language = input_dict.get("language", "python")
        parsed = self.parse_structured_prompt(structured_prompt)
        is_complex = self.is_complex_prompt(structured_prompt)
        if is_complex:
            subtasks = self.generate_subtasks(parsed, structured_prompt, language)
            return subtasks
        else:
            return {
                "subtask_type": "core_algorithm",
                "original_context": structured_prompt,
                "signature": parsed["signature"],
                "instructions": parsed["instructions"],
                "language": language
            } 