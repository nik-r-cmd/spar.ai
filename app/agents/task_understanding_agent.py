"""
TaskUnderstandingAgent for spar.ai: Generates structured prompts using templates and user input.
"""
import yaml
from jinja2 import Template
from typing import Dict
import os

TEMPLATE_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), '../templates/template_registry.yaml')

def load_templates() -> dict:
    """
    Loads the template registry YAML file.
    """
    with open(TEMPLATE_REGISTRY_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def generate_structured_prompt(task_data: Dict) -> Dict:
    """
    Generates a structured prompt using the constraints field to select the template.
    If constraints is 'Not specified' or 'default', use the default template.
    Returns a dict with structured_prompt, language, method_used, and original_prompt.
    """
    templates = load_templates()
    constraints = task_data.get('constraints', 'default')
    if constraints not in templates or constraints in ["Not specified", "default"]:
        template_data = templates['default']
        method_used = 'default'
    else:
        template_data = templates[constraints]
        method_used = constraints
    # Compose the prompt
    prompt = (
        f"# Language: {task_data['language']}\n"
        f"# Task: {task_data['original_prompt']}\n"
        f"# Signature: {template_data['signature']}\n"
        f"# Method: {template_data['method']}\n"
        f"# Edge Cases: {template_data['edge_cases']}"
    )
    return {
        "structured_prompt": prompt,
        "language": task_data["language"],
        "method_used": method_used,
        "original_prompt": task_data["original_prompt"]
    } 