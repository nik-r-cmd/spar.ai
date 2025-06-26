import pytest
from app.modules import input_handler

def test_extract_constraints():
    assert input_handler.extract_constraints("Use binary search on array") == "binary search"
    assert input_handler.extract_constraints("Try two-pointer and stack") == "two-pointer, stack"
    assert input_handler.extract_constraints("No special method") == "Not specified"

def test_get_user_input():
    result = input_handler.get_user_input("Find palindrome", "Python")
    assert result["original_prompt"] == "Find palindrome"
    assert result["language"] == "Python"
    assert result["constraints"] == "Not specified"
    assert isinstance(input_handler.task_history, list)

def test_extract_constraints_sliding_window():
    prompt = "Find the max subarray sum using a window of length k"
    assert input_handler.extract_constraints(prompt) == "sliding_window"

def test_extract_constraints_binary_search():
    prompt = "Search for an element in a sorted array using binary search"
    assert input_handler.extract_constraints(prompt) == "binary_search"

def test_extract_constraints_not_specified():
    prompt = "No special method mentioned"
    assert input_handler.extract_constraints(prompt) == "Not specified"

def test_identify_best_method_sliding_window():
    prompt = "Find the max subarray sum using a window of length k"
    assert input_handler.identify_best_method(prompt) == "sliding_window"

def test_identify_best_method_default():
    prompt = "Completely unrelated problem statement"
    assert input_handler.identify_best_method(prompt) == "default"

def test_get_user_input_with_constraint():
    prompt = "Find the max subarray sum using a window of length k"
    result = input_handler.get_user_input(prompt, "Python")
    assert result["constraints"] == "sliding_window"

def test_get_user_input_fallback():
    prompt = "Completely unrelated problem statement"
    result = input_handler.get_user_input(prompt, "Python")
    assert result["constraints"] == "default"
    assert isinstance(input_handler.task_history, list) 