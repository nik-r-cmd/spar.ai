
from app.agents.task_understanding_agent import generate_structured_prompt

def task_understanding_node(payload: dict) -> dict:
    return generate_structured_prompt(payload) 