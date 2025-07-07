"""
Tests for the refactored TaskUnderstandingAgent module.
"""
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.task_understanding_agent import (
    determine_best_method,
    should_override_method,
    generate_structured_prompt
)

class TestDetermineBestMethod:
    """Test cases for determine_best_method function."""
    
    def test_sliding_window_keywords(self):
        """Test detection of sliding window method from keywords."""
        prompt = "Find maximum subarray sum with fixed length k"
        result = determine_best_method(prompt)
        assert result == "sliding_window"
    
    def test_binary_search_keywords(self):
        """Test detection of binary search method from keywords."""
        prompt = "Search for element in sorted array"
        result = determine_best_method(prompt)
        assert result == "binary_search"
    
    def test_two_pointer_keywords(self):
        """Test detection of two pointer method from keywords."""
        prompt = "Find pair sum using two pointer approach"
        result = determine_best_method(prompt)
        assert result == "two_pointer"
    
    def test_hashmap_keywords(self):
        """Test detection of hashmap method from keywords."""
        prompt = "Use hashmap for lookup"
        result = determine_best_method(prompt)
        assert result == "hashmap"
    
    def test_greedy_keywords(self):
        """Test detection of greedy method from keywords."""
        prompt = "Maximize value with greedy approach"
        result = determine_best_method(prompt)
        assert result == "greedy"
    
    def test_no_keywords_found(self):
        """Test when no keywords match any method."""
        prompt = "Completely unrelated problem statement"
        result = determine_best_method(prompt)
        assert result == "default"
    
    def test_multiple_keywords_highest_count(self):
        """Test that method with highest keyword count is selected."""
        # This test depends on the actual keywords in the template registry
        prompt = "Find maximum subarray sum with sliding window of length k"
        result = determine_best_method(prompt)
        # Should prefer sliding_window over other methods due to more keyword matches
        assert result in ["sliding_window", "default"]

class TestShouldOverrideMethod:
    """Test cases for should_override_method function."""
    
    def test_no_method_specified(self):
        """Test override when no method is specified."""
        should_override, reason = should_override_method("Not specified", "sliding_window", "test prompt")
        assert should_override == True
        assert "No method specified" in reason
        assert "sliding_window" in reason
    
    def test_method_matches_best(self):
        """Test no override when user method matches best method."""
        should_override, reason = should_override_method("sliding_window", "sliding_window", "test prompt")
        assert should_override == False
        assert reason == ""
    
    def test_method_does_not_match_best(self):
        """Test override when user method doesn't match best method."""
        should_override, reason = should_override_method("backtracking", "sliding_window", "Find maximum subarray sum")
        assert should_override == True
        assert "User requested 'backtracking'" in reason
        assert "sliding_window" in reason
    
    def test_override_reason_includes_keywords(self):
        """Test that override reason includes relevant keywords."""
        should_override, reason = should_override_method("backtracking", "sliding_window", "Find maximum subarray sum with fixed length")
        assert should_override == True
        assert "subarray" in reason or "sliding window" in reason

class TestGenerateStructuredPrompt:
    """Test cases for generate_structured_prompt function."""
    
    def test_no_method_specified_override(self):
        """Test when no method is specified and gets overridden."""
        task_data = {
            "original_prompt": "Find maximum subarray sum with fixed length k",
            "language": "Python",
            "method": "Not specified",
            "constraints": "size 10^5"
        }
        result = generate_structured_prompt(task_data)
        
        assert result["language"] == "Python"
        assert result["original_prompt"] == task_data["original_prompt"]
        assert result["method_used"] == "sliding_window"  # Should be determined by keywords
        assert result["overridden_method"] == True
        assert "No method specified" in result["override_reason"]
        assert result["constraints"] == "size 10^5"
        assert "structured_prompt" in result
        assert "edge_cases" in result
    
    def test_method_matches_best_no_override(self):
        """Test when user method matches best method - no override."""
        task_data = {
            "original_prompt": "Find maximum subarray sum with fixed length k",
            "language": "Java",
            "method": "sliding_window",
            "constraints": "no extra space"
        }
        result = generate_structured_prompt(task_data)
        
        assert result["language"] == "Java"
        assert result["method_used"] == "sliding_window"
        assert result["overridden_method"] == False
        assert result["override_reason"] == ""
        assert result["constraints"] == "no extra space"
    
    def test_method_overridden_with_rationale(self):
        """Test when user method is overridden with rationale."""
        task_data = {
            "original_prompt": "Find maximum subarray sum with fixed length k",
            "language": "C++",
            "method": "backtracking",
            "constraints": "O(n) time"
        }
        result = generate_structured_prompt(task_data)
        
        assert result["language"] == "C++"
        assert result["method_used"] == "sliding_window"  # Should override backtracking
        assert result["overridden_method"] == True
        assert "User requested 'backtracking'" in result["override_reason"]
        assert "sliding_window" in result["override_reason"]
        assert result["constraints"] == "O(n) time"
    
    def test_unknown_method_fallback_to_default(self):
        """Test fallback to default when method is not in registry."""
        task_data = {
            "original_prompt": "Completely unrelated problem",
            "language": "Python",
            "method": "unknown_method",
            "constraints": "Not specified"
        }
        result = generate_structured_prompt(task_data)
        
        assert result["method_used"] == "default"
        assert result["overridden_method"] == True
        assert "default" in result["override_reason"]
    
    def test_structured_prompt_format(self):
        """Test that structured prompt has correct format."""
        task_data = {
            "original_prompt": "Test problem",
            "language": "Python",
            "method": "Not specified",
            "constraints": "test constraints"
        }
        result = generate_structured_prompt(task_data)
        
        prompt = result["structured_prompt"]
        assert "# Language: Python" in prompt
        assert "# Task: Test problem" in prompt
        assert "# Signature:" in prompt
        assert "# Method:" in prompt
        assert "# Edge Cases:" in prompt
    
    def test_edge_cases_included(self):
        """Test that edge cases are included in the result."""
        task_data = {
            "original_prompt": "Find maximum subarray sum",
            "language": "Python",
            "method": "sliding_window",
            "constraints": "size 10^5"
        }
        result = generate_structured_prompt(task_data)
        
        assert "edge_cases" in result
        assert result["edge_cases"] is not None
        assert len(result["edge_cases"]) > 0

if __name__ == "__main__":
    pytest.main([__file__]) 