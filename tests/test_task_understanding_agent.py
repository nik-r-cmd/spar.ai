from app.agents import task_understanding_agent

def test_generate_structured_prompt_palindrome():
    task_data = {
        "original_prompt": "Check if string is palindrome",
        "language": "Python",
        "constraints": "Not specified"
    }
    result = task_understanding_agent.generate_structured_prompt(task_data)
    assert "is_palindrome" in result["structured_prompt"]
    assert result["language"] == "Python"

def test_generate_structured_prompt_sliding_window():
    task_data = {
        "original_prompt": "Find the max subarray sum using a window of length k",
        "language": "Python",
        "constraints": "sliding_window"
    }
    result = task_understanding_agent.generate_structured_prompt(task_data)
    assert "sliding window" in result["structured_prompt"].lower()
    assert result["method_used"] == "sliding_window"
    assert result["language"] == "Python"

def test_generate_structured_prompt_binary_search():
    task_data = {
        "original_prompt": "Search for an element in a sorted array using binary search",
        "language": "Python",
        "constraints": "binary_search"
    }
    result = task_understanding_agent.generate_structured_prompt(task_data)
    assert "binary search" in result["structured_prompt"].lower()
    assert result["method_used"] == "binary_search"

def test_generate_structured_prompt_default():
    task_data = {
        "original_prompt": "Completely unrelated problem statement",
        "language": "Python",
        "constraints": "Not specified"
    }
    result = task_understanding_agent.generate_structured_prompt(task_data)
    assert "solution" in result["structured_prompt"].lower()
    assert result["method_used"] == "default" 