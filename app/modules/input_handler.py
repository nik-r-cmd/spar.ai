"""
InputHandler module for spar.ai: Handles user input, extracts constraints, and maintains task history.
"""
import re
import yaml
import os
from datetime import datetime
from typing import List, Dict

TEMPLATE_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), '../templates/template_registry.yaml')

def load_method_keywords() -> dict:
    """
    Loads the method keywords from the YAML registry.
    Returns a dict of {method_name: [keywords]}.
    """
    with open(TEMPLATE_REGISTRY_PATH, 'r', encoding='utf-8') as f:
        templates = yaml.safe_load(f)
    return {k: v.get('keywords', []) for k, v in templates.items() if 'keywords' in v}

def _count_keyword_hits(prompt: str, method_keywords: dict) -> dict:
    """
    Returns a dict of {method: hit_count} for the given prompt.
    """
    prompt_lower = prompt.lower()
    hit_counts = {}
    for method, keywords in method_keywords.items():
        count = 0
        for kw in keywords:
            if re.search(rf'\b{re.escape(kw.lower())}\b', prompt_lower):
                count += 1
        if count > 0:
            hit_counts[method] = count
    return hit_counts

def extract_constraints(prompt: str) -> str:
    """
    Scans the prompt for all known method keywords from the YAML registry.
    Returns the method with the highest keyword hit count, or 'Not specified' if none.
    """
    method_keywords = load_method_keywords()
    hit_counts = _count_keyword_hits(prompt, method_keywords)
    if hit_counts:
        # Return the method with the highest hit count (break ties arbitrarily)
        return max(hit_counts, key=lambda m: hit_counts[m])
    return "Not specified"

def identify_best_method(prompt: str) -> str:
    """
    Suggests the most relevant method by counting keyword hits in the YAML registry.
    Returns the method with the highest hit count, or 'default' if none.
    """
    method_keywords = load_method_keywords()
    hit_counts = _count_keyword_hits(prompt, method_keywords)
    if hit_counts:
        return max(hit_counts, key=lambda m: hit_counts[m])
    return "default"

task_history: List[Dict] = []

def get_user_input(problem_text: str, language: str) -> dict:
    """
    Processes user input and language selection, extracts constraints, and stores in task_history.
    If constraints are not found, uses identify_best_method.
    Returns a dictionary with original prompt, language, and constraints.
    """
    constraints = extract_constraints(problem_text)
    if constraints == "Not specified":
        constraints = identify_best_method(problem_text)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "original_prompt": problem_text,
        "language": language,
        "constraints": constraints
    }
    task_history.append(entry)
    return {
        "original_prompt": problem_text,
        "language": language,
        "constraints": constraints
    } 