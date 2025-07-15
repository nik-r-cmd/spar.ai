import re
import yaml
import os
from datetime import datetime
from typing import List, Dict, Optional
from textblob import TextBlob
from collections import defaultdict, deque
import json
import requests
import logging
from enum import Enum

TEMPLATE_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), '../templates/template_registry.yaml')

# LLM mode config
class LLMMode(Enum):
    AUTO = 'auto'
    LLM_ONLY = 'llm_only'
    HEURISTIC_ONLY = 'heuristic_only'
    MOCK = 'mock'

LLM_MODE: LLMMode = LLMMode.AUTO  # Change as needed

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def load_method_keywords() -> dict:
    """
    Load method keywords from the template registry YAML file.
    Returns a dict mapping method names to their keywords.
    """
    with open(TEMPLATE_REGISTRY_PATH, 'r', encoding='utf-8') as f:
        templates = yaml.safe_load(f)
    return {k: v.get('keywords', []) for k, v in templates.items() if 'keywords' in v}

def load_test_case_patterns() -> dict:
    """
    Load test case patterns from the template registry YAML file.
    Returns a dict with 'regexes' and 'keywords'.
    """
    with open(TEMPLATE_REGISTRY_PATH, 'r', encoding='utf-8') as f:
        templates = yaml.safe_load(f)
    return templates.get('test_case_patterns', {})

def load_constraint_patterns() -> dict:
    """
    Load constraint patterns from the template registry YAML file.
    Returns a dict with 'regexes' and 'keywords'.
    """
    with open(TEMPLATE_REGISTRY_PATH, 'r', encoding='utf-8') as f:
        templates = yaml.safe_load(f)
    return templates.get('constraint_patterns', {})

def extract_explicit_method(prompt: str) -> str:
    """
    Extract the explicit method mentioned in the prompt, if any.
    Returns the method name or "Not specified".
    """
    prompt_lower = prompt.lower()
    method_keywords = load_method_keywords()
    # Look for explicit method mentions
    explicit_patterns = [
        r'use\s+(\w+(?:\s+\w+)*)',  # "use binary search"
        r'don\'?t?\s+use\s+(\w+(?:\s+\w+)*)',  # "don't use recursion"
        r'no\s+(\w+(?:\s+\w+)*)',  # "no recursion"
        r'with\s+(\w+(?:\s+\w+)*)',  # "with sliding window"
        r'using\s+(\w+(?:\s+\w+)*)',  # "using hashmap"
    ]
    for pattern in explicit_patterns:
        matches = re.findall(pattern, prompt_lower)
        for match in matches:
            for method_name, keywords in method_keywords.items():
                if method_name.lower() in match or any(kw.lower() in match for kw in keywords):
                    return method_name
    return "Not specified"

def extract_test_cases(prompt: str) -> str:
    """
    Extract test cases from the prompt using regexes and keywords from the template registry.
    Returns a string with extracted test cases or 'Not specified'.
    """
    patterns = load_test_case_patterns()
    regexes = patterns.get('regexes', [])
    keywords = patterns.get('keywords', [])
    test_cases = []
    for regex in regexes:
        matches = re.findall(regex, prompt, re.IGNORECASE)
        for match in matches:
            test_cases.append(match if isinstance(match, str) else ' '.join(match))
    for keyword in keywords:
        if keyword in prompt.lower():
            test_cases.append(keyword)
    return ', '.join(set(test_cases)) if test_cases else 'Not specified'

def extract_constraints(prompt: str) -> str:
    """
    Extract constraints (e.g., time/space, additional patterns) from the prompt, if any.
    Returns the constraint string or "Not specified".
    """
    constraints = []
    # Numerical constraints
    size_patterns = [
        r'size\s+(\d+(?:\^\d+)?)',  # "size 10^5"
        r'(\d+(?:\^\d+)?)\s+elements',  # "10^5 elements"
        r'array\s+of\s+(\d+(?:\^\d+)?)',  # "array of 10^5"
    ]
    for pattern in size_patterns:
        matches = re.findall(pattern, prompt, re.IGNORECASE)
        for match in matches:
            constraints.append(f"size {match}")
    # Time complexity constraints
    complexity_patterns = [
        r'O\([^)]+\)',  # "O(n log n)", "O(1)"
        r'time\s+complexity\s+([^,\.]+)',  # "time complexity O(n)"
    ]
    for pattern in complexity_patterns:
        matches = re.findall(pattern, prompt, re.IGNORECASE)
        for match in matches:
            constraints.append(f"time complexity {match}")
    # Space constraints
    space_patterns = [
        r'no\s+extra\s+space',
        r'in\s+place',
        r'constant\s+space',
        r'O\(1\)\s+space',
    ]
    for pattern in space_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            constraints.append("no extra space")
    # Other common constraints - use simple string matching instead of regex
    if re.search(r'unsorted\s+array', prompt, re.IGNORECASE):
        constraints.append("unsorted array")
    if re.search(r'sorted\s+array', prompt, re.IGNORECASE):
        constraints.append("sorted array")
    if re.search(r'duplicates\s+allowed', prompt, re.IGNORECASE):
        constraints.append("duplicates allowed")
    if re.search(r'no\s+duplicates', prompt, re.IGNORECASE):
        constraints.append("no duplicates")
    if re.search(r'positive\s+integers', prompt, re.IGNORECASE):
        constraints.append("positive integers")
    if re.search(r'negative\s+numbers', prompt, re.IGNORECASE):
        constraints.append("negative numbers")
    # Additional patterns from template registry
    patterns = load_constraint_patterns()
    regexes = patterns.get('regexes', [])
    keywords = patterns.get('keywords', [])
    for regex in regexes:
        matches = re.findall(regex, prompt, re.IGNORECASE)
        for match in matches:
            constraints.append(match if isinstance(match, str) else ' '.join(match))
    for keyword in keywords:
        if keyword in prompt.lower():
            constraints.append(keyword)
    return ", ".join(set(constraints)) if constraints else "Not specified"

task_history: List[Dict] = []

def preprocess_user_input(prompt: str) -> dict:
    """
    Cleans, normalizes, corrects typos, and detects ambiguities in the user prompt.
    Returns a dict with cleaned_prompt, corrected_prompt, and ambiguity_flags.
    """
    # Basic cleaning
    cleaned = prompt.strip().replace("\n", " ")
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # Typo correction
    blob = TextBlob(cleaned)
    corrected = str(blob.correct())
    # Ambiguity detection (simple heuristics)
    ambiguous_phrases = [
        "somehow", "maybe", "possibly", "etc", "something", "stuff", "thing", "things", "various", "could be", "might be", "sort of", "kind of", "approximately", "about", "around", "probably", "likely", "unclear", "ambiguous", "not sure", "not certain"
    ]
    ambiguity_flags = [phrase for phrase in ambiguous_phrases if phrase in cleaned.lower()]
    # Also flag if the prompt is very short or lacks verbs
    if len(cleaned.split()) < 5:
        ambiguity_flags.append("Prompt too short")
    if not re.search(r'\b(is|are|do|does|find|compute|return|implement|write|solve|check|determine|print|output)\b', cleaned, re.IGNORECASE):
        ambiguity_flags.append("No clear action verb detected")
    return {
        "cleaned_prompt": cleaned,
        "corrected_prompt": corrected,
        "ambiguity_flags": ambiguity_flags
    }

def get_user_input(problem_text: str, language: str) -> dict:
    """
    Process user input: clean, correct typos, detect ambiguities, extract method, constraints, and test cases.
    Returns a dict with all processed fields.
    """
    preprocess_result = preprocess_user_input(problem_text)
    cleaned_prompt = preprocess_result["cleaned_prompt"]
    corrected_prompt = preprocess_result["corrected_prompt"]
    ambiguity_flags = preprocess_result["ambiguity_flags"]
    method = extract_explicit_method(cleaned_prompt)
    constraints = extract_constraints(cleaned_prompt)
    test_cases = extract_test_cases(cleaned_prompt)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "original_prompt": problem_text,
        "cleaned_prompt": cleaned_prompt,
        "corrected_prompt": corrected_prompt,
        "ambiguity_flags": ambiguity_flags,
        "language": language,
        "method": method,
        "constraints": constraints,
        "test_cases": test_cases
    }
    task_history.append(entry)
    return {
        "original_prompt": problem_text,
        "cleaned_prompt": cleaned_prompt,
        "corrected_prompt": corrected_prompt,
        "ambiguity_flags": ambiguity_flags,
        "language": language,
        "method": method,
        "constraints": constraints,
        "test_cases": test_cases
    }

class Subtask:
    """
    Represents a single subtask in the DAG, with dependencies, status, result, and error info.
    """
    def __init__(self, name: str, prompt: str, depends_on: Optional[list] = None):
        self.name: str = name
        self.prompt: str = prompt
        self.depends_on: list = depends_on or []  # List of subtask names
        self.status: str = 'pending'  # pending, running, done, failed
        self.result: Optional[str] = None
        self.error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'prompt': self.prompt,
            'depends_on': self.depends_on,
            'status': self.status,
            'result': self.result,
            'error': self.error
        }

class SubtaskDAG:
    """
    Directed acyclic graph (DAG) of subtasks for parallel execution and dependency management.
    """
    def __init__(self) -> None:
        self.subtasks: dict[str, Subtask] = {}
        self.edges: defaultdict[str, list] = defaultdict(list)  # name -> list of dependent names

    def add_subtask(self, subtask: Subtask) -> None:
        """Add a subtask to the DAG."""
        self.subtasks[subtask.name] = subtask
        for dep in subtask.depends_on:
            self.edges[dep].append(subtask.name)

    def get_ready_subtasks(self) -> list[Subtask]:
        """Return subtasks with all dependencies done and status pending."""
        ready = []
        for name, subtask in self.subtasks.items():
            if subtask.status == 'pending' and all(
                self.subtasks[dep].status == 'done' for dep in subtask.depends_on
            ):
                ready.append(subtask)
        return ready

    def to_dict(self) -> dict:
        """Return a dict representation of the DAG."""
        return {name: subtask.to_dict() for name, subtask in self.subtasks.items()}

class SubtaskDistributor:
    """
    Analyzes structured prompts and determines whether to route them as atomic tasks or decompose them into subtasks for further processing.
    Models subtasks as a DAG for parallel execution and dependency management.
    Handles LLM/heuristic/mock fallback.
    """
    def __init__(self) -> None:
        """Initialize SubtaskDistributor."""
        pass

    def llm_classify_task(self, prompt: str) -> tuple[dict | None, bool]:
        """
        Classify task complexity using heuristic only (no microservice call).
        Returns (result, fallback_used).
        """
        # Always use heuristic fallback
        return None, True  # Fallback used

    def llm_decompose_task(self, prompt: str) -> tuple[dict | None, bool]:
        """
        Decompose task into subtasks using heuristic only (no microservice call).
        Returns (result, fallback_used).
        """
        # Always use heuristic fallback
        return None, True

    def is_complex_task(self, prompt: str) -> tuple[bool, bool]:
        """
        Determine if task is complex using LLM or heuristic.
        Returns (is_complex, fallback_used).
        """
        llm_result, fallback_used = self.llm_classify_task(prompt)
        if llm_result and 'classification' in llm_result:
            return llm_result['classification'] == 'complex', fallback_used
        # Fallback to heuristic
        complexity_keywords = [
            "validate", "check if", "after that", "finally", "then", "ensure", "before that", "next", "subtask", "step", "first", "second", "third", "repeat", "loop", "for each", "if", "while", "until", "combine", "merge", "split", "sort", "search", "traverse", "build", "construct", "return", "output", "input", "format", "convert", "parse", "calculate", "determine", "find", "implement", "write", "solve", "process", "handle", "case", "edge case", "base case", "recursive", "iterative", "dynamic", "greedy", "backtrack", "divide", "conquer", "memoize", "cache", "optimize", "maximize", "minimize", "count", "sum", "product", "difference", "intersection", "union", "subset", "superset", "permutation", "combination", "sequence", "array", "list", "tree", "graph", "node", "edge", "vertex", "path", "cycle", "component", "connected", "disconnected", "directed", "undirected", "weighted", "unweighted", "adjacent", "neighbor", "parent", "child", "ancestor", "descendant", "leaf", "root", "depth", "height", "level", "distance", "shortest", "longest", "minimum", "maximum", "average", "median", "mode", "frequency", "occurrence", "repeat", "duplicate", "unique", "distinct", "continuous", "consecutive", "increasing", "decreasing", "sorted", "unsorted", "random", "shuffle", "sample", "pick", "select", "choose", "extract", "remove", "delete", "insert", "add", "append", "prepend", "push", "pop", "enqueue", "dequeue", "stack", "queue", "priority queue", "heap", "binary heap", "min heap", "max heap", "hash", "hashmap", "dictionary", "set", "map", "filter", "reduce", "fold", "scan", "accumulate", "aggregate", "group", "partition", "split", "join", "merge", "combine", "concatenate", "flatten", "expand", "compress", "encode", "decode", "serialize", "deserialize", "parse", "format", "convert", "cast", "type", "class", "object", "instance", "attribute", "property", "field", "member", "method", "function", "procedure", "routine", "subroutine", "lambda", "closure", "callback", "event", "listener", "handler", "signal", "slot", "thread", "process", "task", "job", "worker", "pool", "queue", "buffer", "stream", "pipe", "channel", "socket", "connection", "session", "transaction", "commit", "rollback", "lock", "unlock", "synchronize", "concurrent", "parallel", "asynchronous", "synchronous", "blocking", "non-blocking", "wait", "notify", "signal", "broadcast", "publish", "subscribe", "observer", "observable", "event", "trigger", "hook", "callback", "handler", "listener", "watcher", "monitor", "logger", "tracer", "profiler", "debugger", "tester", "validator", "checker", "inspector", "analyzer", "parser", "lexer", "scanner", "tokenizer", "interpreter", "compiler", "assembler", "linker", "loader", "executor", "runner", "driver", "controller", "manager", "coordinator", "scheduler", "dispatcher", "router", "switch", "gateway", "proxy", "firewall", "filter", "transformer", "converter", "adapter", "wrapper", "decorator", "proxy", "facade", "bridge", "adapter", "composite", "flyweight", "singleton", "factory", "builder", "prototype", "abstract", "interface", "implementation", "inheritance", "polymorphism", "encapsulation", "abstraction", "composition", "aggregation", "association", "dependency", "coupling", "cohesion", "modularity", "reusability", "extensibility", "scalability", "maintainability", "testability", "portability", "interoperability", "compatibility", "usability", "accessibility", "security", "privacy", "confidentiality", "integrity", "availability", "reliability", "robustness", "fault tolerance", "resilience", "redundancy", "backup", "restore", "recovery", "failover", "load balancing", "scaling", "sharding", "partitioning", "replication", "synchronization", "consistency", "concurrency", "parallelism", "distribution", "communication", "coordination", "collaboration", "integration", "interfacing", "interaction", "exchange", "sharing", "publishing", "subscribing", "notifying", "signaling", "triggering", "invoking", "calling", "executing", "running", "processing", "handling"]
        
        if prompt.count(".") > 0 or ";" in prompt:
            return True, True
        sentences = re.split(r'[.?!;\n]', prompt)
        imperative_count = 0
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            first_word = s.split()[0].lower() if s.split() else ""
            if first_word in [k.split()[0] for k in complexity_keywords]:
                imperative_count += 1
            for kw in complexity_keywords:
                if kw in s.lower():
                    imperative_count += 1
                    break
        if imperative_count > 0:
            return True, True
        if len(prompt.split()) > 15:
            return True, True
        return False, True

    def extract_subtasks(self, prompt: str) -> tuple[list, bool]:
        """
        Extract subtasks using LLM or heuristic.
        Returns (subtasks, fallback_used).
        """
        llm_result, fallback_used = self.llm_decompose_task(prompt)
        if llm_result and 'subtasks' in llm_result and llm_result['subtasks']:
            subtasks = []
            for sub in llm_result['subtasks']:
                name = sub.get('name', 'Subtask')
                desc = sub.get('description', '')
                depends_on = sub.get('depends_on', [])
                subtasks.append((name, desc, depends_on))
            return subtasks, fallback_used
        # Fallback to heuristic
        steps = re.split(r'\b(?:step|first|second|third|then|after that|next|finally|;|\.)\b', prompt, flags=re.IGNORECASE)
        steps = [s.strip() for s in steps if s.strip()]
        subtasks = []
        for idx, step in enumerate(steps):
            name = f"Step {idx+1}"
            depends_on = [f"Step {idx}"] if idx > 0 else []
            subtasks.append((name, step, depends_on))
        # If no clear steps, treat as a single subtask
        if not subtasks:
            subtasks = [("Core Logic", prompt, [])]
        return subtasks, True

    def distribute_task(self, input_dict: dict) -> tuple['SubtaskDAG', bool]:
        """
        Distribute task into a DAG of subtasks.
        Returns (dag, fallback_used).
        """
        structured_prompt = input_dict.get("structured_prompt", "")
        original_prompt = input_dict.get("original_prompt", "")
        complexity = input_dict.get("complexity")
        fallback_used = False
        if complexity is None:
            is_complex, fallback_used = self.is_complex_task(structured_prompt or original_prompt)
            complexity = "complex" if is_complex else "simple"
        input_dict["complexity"] = complexity
        if complexity == "simple":
            dag = SubtaskDAG()
            sub = Subtask("Core Logic", structured_prompt or original_prompt)
            dag.add_subtask(sub)
            return dag, fallback_used
        subtasks_info, fallback_used = self.extract_subtasks(structured_prompt or original_prompt)
        dag = SubtaskDAG()
        for name, prompt, depends_on in subtasks_info:
            dag.add_subtask(Subtask(name, prompt, depends_on))
        return dag, fallback_used 