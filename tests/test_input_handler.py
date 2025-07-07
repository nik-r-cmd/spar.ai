"""
Tests for the refactored InputHandler module.
"""
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.modules.input_handler import (
    extract_explicit_method,
    extract_constraints,
    get_user_input
)

class TestExtractExplicitMethod:
    """Test cases for extract_explicit_method function."""
    
    def test_explicit_binary_search(self):
        """Test extraction of explicitly mentioned binary search."""
        prompt = "Use binary search on the sorted array of size 10^5"
        result = extract_explicit_method(prompt)
        assert result == "binary_search"
    
    def test_explicit_sliding_window(self):
        """Test extraction of explicitly mentioned sliding window."""
        prompt = "Find maximum subarray sum using sliding window"
        result = extract_explicit_method(prompt)
        assert result == "sliding_window"
    
    def test_explicit_dont_use_recursion(self):
        """Test extraction of 'don't use' statements."""
        prompt = "Don't use recursion for this problem"
        result = extract_explicit_method(prompt)
        assert result == "backtracking"  # 'recursion' is a keyword for backtracking in our registry
    
    def test_explicit_with_statement(self):
        """Test extraction using 'with' keyword."""
        prompt = "Solve this with hashmap approach"
        result = extract_explicit_method(prompt)
        assert result == "hashmap"
    
    def test_explicit_using_statement(self):
        """Test extraction using 'using' keyword."""
        prompt = "Using two pointer technique"
        result = extract_explicit_method(prompt)
        assert result == "two_pointer"
    
    def test_no_explicit_method(self):
        """Test when no method is explicitly mentioned."""
        prompt = "Find the maximum sum of a subarray"
        result = extract_explicit_method(prompt)
        assert result == "Not specified"
    
    def test_case_insensitive(self):
        """Test that method extraction is case insensitive."""
        prompt = "USE BINARY SEARCH for this problem"
        result = extract_explicit_method(prompt)
        assert result == "binary_search"

class TestExtractConstraints:
    """Test cases for extract_constraints function."""
    
    def test_size_constraint(self):
        """Test extraction of size constraints."""
        prompt = "Array of size 10^5"
        result = extract_constraints(prompt)
        assert "size 10^5" in result
    
    def test_time_complexity_constraint(self):
        """Test extraction of time complexity constraints."""
        prompt = "Must be O(n log n) time complexity"
        result = extract_constraints(prompt)
        assert "time complexity O(n log n)" in result
    
    def test_space_constraint(self):
        """Test extraction of space constraints."""
        prompt = "No extra space allowed"
        result = extract_constraints(prompt)
        assert "no extra space" in result
    
    def test_sorted_array_constraint(self):
        """Test extraction of array type constraints."""
        prompt = "Given a sorted array"
        result = extract_constraints(prompt)
        assert "sorted array" in result
    
    def test_multiple_constraints(self):
        """Test extraction of multiple constraints."""
        prompt = "Sorted array of size 10^5, no extra space, O(n log n)"
        result = extract_constraints(prompt)
        assert "size 10^5" in result
        assert "no extra space" in result
        assert "time complexity O(n log n)" in result
        assert "sorted array" in result
    
    def test_no_constraints(self):
        """Test when no constraints are mentioned."""
        prompt = "Find the maximum element"
        result = extract_constraints(prompt)
        assert result == "Not specified"
    
    def test_case_insensitive_constraints(self):
        """Test that constraint extraction is case insensitive."""
        prompt = "SORTED ARRAY of SIZE 10^5"
        result = extract_constraints(prompt)
        assert "sorted array" in result
        assert "size 10^5" in result

class TestGetUserInput:
    """Test cases for get_user_input function."""
    
    def test_complete_input_processing(self):
        """Test complete input processing with method and constraints."""
        prompt = "Use binary search on sorted array of size 10^5"
        result = get_user_input(prompt, "Python")
        
        assert result["original_prompt"] == prompt
        assert result["language"] == "Python"
        assert result["method"] == "binary_search"
        assert "size 10^5" in result["constraints"]
        assert "sorted array" in result["constraints"]
    
    def test_input_without_explicit_method(self):
        """Test input processing when no method is explicitly mentioned."""
        prompt = "Find maximum subarray sum"
        result = get_user_input(prompt, "Java")
        
        assert result["original_prompt"] == prompt
        assert result["language"] == "Java"
        assert result["method"] == "Not specified"
        assert result["constraints"] == "Not specified"
    
    def test_input_with_constraints_only(self):
        """Test input processing with constraints but no explicit method."""
        prompt = "Array of size 10^6, no extra space"
        result = get_user_input(prompt, "C++")
        
        assert result["original_prompt"] == prompt
        assert result["language"] == "C++"
        assert result["method"] == "Not specified"
        assert "size 10^6" in result["constraints"]
        assert "no extra space" in result["constraints"]
    
    def test_task_history_storage(self):
        """Test that input is stored in task history."""
        from app.modules.input_handler import task_history
        initial_length = len(task_history)
        
        prompt = "Test prompt"
        get_user_input(prompt, "Python")
        
        assert len(task_history) == initial_length + 1
        assert task_history[-1]["original_prompt"] == prompt
        assert task_history[-1]["language"] == "Python"

if __name__ == "__main__":
    pytest.main([__file__]) 