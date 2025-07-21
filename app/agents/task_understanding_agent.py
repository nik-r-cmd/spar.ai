"""
TaskUnderstandingAgent for spar.ai: Generates structured prompts using templates and user input.
Determines the best method and overrides user-provided methods when needed.
"""

import yaml
from jinja2 import Template
from typing import Dict
import os
import re
import difflib
import nltk
from nltk.stem import WordNetLemmatizer
nltk.download('wordnet', quiet=True)

TEMPLATE_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), '../templates/template_registry.yaml')

lemmatizer = WordNetLemmatizer()

def load_templates() -> dict:
    """
    Loads the template registry YAML file.
    Returns a dictionary of templates.
    """
    with open(TEMPLATE_REGISTRY_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def _normalize(text: str) -> str:
    """
    Normalize text by lowercasing and lemmatizing all words.
    Returns the normalized string.
    """
    return ' '.join([lemmatizer.lemmatize(w) for w in re.findall(r'\w+', text.lower())])

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

def determine_best_method(prompt: str) -> str:
    """
    Determines the best-fit method using keyword analysis from the template registry.
    Returns the method with the highest keyword hit count, or 'default' if none.
    """
    templates = load_templates()
    method_keywords = {k: v.get('keywords', []) for k, v in templates.items() if 'keywords' in v}
    prompt_norm = _normalize(prompt)
    # 1. Exact and lemmatized keyword match
    best_method = None
    best_score = 0
    for method, keywords in method_keywords.items():
        for kw in keywords:
            kw_norm = _normalize(kw)
            if kw_norm in prompt_norm:
                score = len(kw_norm)
                if score > best_score:
                    best_score = score
                    best_method = method
    if best_method:
        return best_method
    # 2. Fuzzy match using difflib
    all_keywords = [(method, kw) for method, kws in method_keywords.items() for kw in kws]
    prompt_words = prompt_norm.split()
    best_method = None
    best_ratio = 0.0
    for method, kw in all_keywords:
        kw_norm = _normalize(kw)
        ratio = difflib.SequenceMatcher(None, kw_norm, prompt_norm).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_method = method
    if best_method and best_ratio > 0.6:
        return best_method
    # 3. Fallback: use the method with the most keyword overlaps
    overlap_counts = {method: 0 for method in method_keywords}
    for method, keywords in method_keywords.items():
        for kw in keywords:
            for word in _normalize(kw).split():
                if word in prompt_words:
                    overlap_counts[method] += 1
    if max(overlap_counts.values()) > 0:
        return max(overlap_counts, key=lambda m: overlap_counts[m])
    return "default"

def should_override_method(user_method: str, best_method: str, prompt: str) -> tuple[bool, str]:
    """
    Determines if the user-provided method should be overridden.
    Returns (should_override, reason).
    """
    if user_method == "Not specified":
        return True, f"No method specified, using best-fit method '{best_method}' based on keyword analysis."
    
    if user_method == best_method:
        return False, ""
    
    # Get keywords for both methods to provide better rationale
    templates = load_templates()
    user_keywords = templates.get(user_method, {}).get('keywords', [])
    best_keywords = templates.get(best_method, {}).get('keywords', [])
    
    # More flexible keyword match: all words in keyword must be present in prompt (case-insensitive)
    prompt_lower = prompt.lower()
    def all_words_in_prompt(keyword):
        return all(word in prompt_lower for word in keyword.lower().split())
    present_keywords = [kw for kw in best_keywords if all_words_in_prompt(kw)]
    
    reason = f"User requested '{user_method}', but based on keywords '{', '.join(present_keywords)}' in the prompt, '{best_method}' is more optimal."
    
    return True, reason

def generate_structured_prompt(task_data: Dict) -> Dict:
    """
    Generates a structured prompt using the best-fit method.
    Compares user-provided method with best-fit method and overrides if needed.
    Returns a dict with structured_prompt, language, method_used, overridden_method, override_reason, edge_cases, constraints, and original_prompt.
    """
    templates = load_templates()
    print(f"[DEBUG] Loaded templates: {list(templates.keys())}")
    user_method = task_data.get('method', 'Not specified')
    original_prompt = task_data.get('original_prompt', '')
    # Determine the best method using keyword analysis
    best_method = determine_best_method(original_prompt)
    print(f"[DEBUG] Best method selected: {best_method}")
    # Check if we should override the user's method
    should_override, override_reason = should_override_method(user_method, best_method, original_prompt)
    # Use the best method (either user's or overridden)
    method_used = best_method if should_override else user_method
    # Get template data
    if method_used not in templates:
        template_data = templates.get('default', {})
    else:
        template_data = templates[method_used]
    # Safely get template values with defaults
    signature = template_data.get('signature', 'def solution():')
    method_desc = template_data.get('method', 'Choose the optimal algorithm or data structure.')
    edge_cases = template_data.get('edge_cases', 'Handle empty input and large inputs.')
    # Compose the prompt
    prompt = (
        f"# Language: {task_data['language']}\n"
        f"# Task: {original_prompt}\n"
        f"# Signature: {signature}\n"
        f"# Method: {method_desc}\n"
        f"# Edge Cases: {edge_cases}\n"
        f"# Constraints: {task_data.get('constraints', 'Not specified')}\n"
        f"# Instructions: Add inline error handling for all possible runtime errors and invalid inputs. Handle all listed edge cases explicitly in the code. Ensure the solution is robust and covers edge scenarios."
    )
    # Optionally include test cases if present
    test_cases = task_data.get('test_cases', None)
    if test_cases and test_cases != 'Not specified':
        prompt += f"\n# Test Cases: {test_cases}"
    # Always return method_used, even if default
    return {
        "structured_prompt": prompt,
        "language": task_data["language"],
        "method_used": method_used if method_used else "default",
        "overridden_method": should_override,
        "override_reason": override_reason if should_override else "",
        "edge_cases": edge_cases,
        "constraints": task_data.get('constraints', 'Not specified'),
        "original_prompt": original_prompt
    } 