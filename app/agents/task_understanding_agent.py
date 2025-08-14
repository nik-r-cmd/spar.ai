import yaml
from jinja2 import Template
from typing import Dict
import os
import re
import difflib
import nltk
from nltk.stem import WordNetLemmatizer
nltk.download('wordnet', quiet=True)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMPLATE_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), '../templates/template_registry.yaml')

lemmatizer = WordNetLemmatizer()

def load_templates() -> dict:
    with open(TEMPLATE_REGISTRY_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def _normalize(text: str) -> str:
    return ' '.join([lemmatizer.lemmatize(w) for w in re.findall(r'\w+', text.lower())])

def _count_keyword_hits(prompt: str, method_keywords: dict) -> dict:
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
    templates = load_templates()
    method_keywords = {k: v.get('keywords', []) for k, v in templates.items() if 'keywords' in v}
    prompt_norm = _normalize(prompt)
    prompt_lower = prompt.lower()
    
    numerical_keywords = ["number", "prime", "factorial", "divisible", "integer", "numeric", "math", "sum", "product"]
    primality_keywords = ["prime", "primality", "divisor"]
    is_numerical = any(kw in prompt_lower for kw in numerical_keywords)
    is_primality = any(kw in prompt_lower for kw in primality_keywords)
    
    best_method = None
    best_score = 0
    for method, keywords in method_keywords.items():
        for kw in keywords:
            kw_norm = _normalize(kw)
            if kw_norm in prompt_norm or kw.lower() in prompt_lower:
                score = len(kw_norm.split())
                if score > best_score:
                    best_score = score
                    best_method = method
    logger.info(f"Exact match score: {best_score}, Method: {best_method}")

    if is_primality and "primality_test" in templates:
        logger.info("Primality keyword detected, prioritizing primality_test")
        return "primality_test"

    if not best_method and not is_primality:
        all_keywords = [(method, kw) for method, kws in method_keywords.items() for kw in kws]
        prompt_words = prompt_norm.split()
        best_ratio = 0.0
        for method, kw in all_keywords:
            kw_norm = _normalize(kw)
            ratio = difflib.SequenceMatcher(None, kw_norm, prompt_norm).ratio()
            if ratio > 0.85:
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_method = method
        logger.info(f"Fuzzy match ratio: {best_ratio}, Method: {best_method}")

    if not best_method and not is_primality:
        overlap_counts = {method: 0 for method in method_keywords}
        for method, keywords in method_keywords.items():
            for kw in keywords:
                for word in _normalize(kw).split():
                    if word in prompt_words:
                        overlap_counts[method] += 1
        if max(overlap_counts.values()) > 0:
            best_method = max(overlap_counts, key=lambda m: overlap_counts[m])
        logger.info(f"Keyword overlap counts: {overlap_counts}, Best Method: {best_method}")

    if is_numerical and not best_method and not is_primality:
        logger.info("Numerical problem with no strong match, falling back to default")
        return "default"
    
    return best_method if best_method else "default"

def should_override_method(user_method: str, best_method: str, prompt: str) -> tuple[bool, str]:
    if user_method == "Not specified":
        return True, f"No method specified, using best-fit method '{best_method}' based on keyword analysis."
    
    if user_method == best_method:
        return False, ""
    
    templates = load_templates()
    user_keywords = templates.get(user_method, {}).get('keywords', [])
    best_keywords = templates.get(best_method, {}).get('keywords', [])
    
    prompt_lower = prompt.lower()
    def all_words_in_prompt(keyword):
        return all(word in prompt_lower for word in keyword.lower().split())
    present_keywords = [kw for kw in best_keywords if all_words_in_prompt(kw)]
    
    reason = f"User requested '{user_method}', but based on keywords '{', '.join(present_keywords)}' in the prompt, '{best_method}' is more optimal."
    return True, reason

def generate_structured_prompt(task_data: Dict) -> Dict:
    templates = load_templates()
    logger.info(f"Loaded templates: {list(templates.keys())}")
    user_method = task_data.get('method', 'Not specified')
    original_prompt = task_data.get('original_prompt', '')
    best_method = determine_best_method(original_prompt)
    logger.info(f"Best method selected: {best_method}")
    should_override, override_reason = should_override_method(user_method, best_method, original_prompt)
    method_used = best_method if should_override else user_method
    if method_used not in templates:
        template_data = templates.get('default', {})
    else:
        template_data = templates[method_used]
    signature = template_data.get('signature', 'def solution():')
    method_desc = template_data.get('method', 'Choose the optimal algorithm or data structure.')
    edge_cases = template_data.get('edge_cases', 'Handle empty input and large inputs.')
    prompt = (
        f"# Language: {task_data['language']}\n"
        f"# Task: {original_prompt}\n"
        f"# Signature: {signature}\n"
        f"# Method: {method_desc}\n"
        f"# Edge Cases: {edge_cases}\n"
        f"# Constraints: {task_data.get('constraints', 'Not specified')}\n"
        f"# Instructions: Add inline error handling for all possible runtime errors and invalid inputs. Handle all listed edge cases explicitly in the code. Ensure the solution is robust and covers edge scenarios."
    )
    test_cases = task_data.get('test_cases', None)
    if test_cases and test_cases != 'Not specified':
        prompt += f"\n# Test Cases: {test_cases}"
    return {
        "structured_prompt": prompt,
        "language": task_data["language"],
        "method_used": method_used if method_used else "default",
        "overridden_method": should_override,
        "override_reason": override_reason if should_override else "",
        "edge_cases": edge_cases,
        "constraints": task_data.get('constraints', 'Not specified'),
        "original_prompt": original_prompt,
        "signature": signature
    }