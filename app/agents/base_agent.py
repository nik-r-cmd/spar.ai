# app/agents/base_agent.py
import threading
from dataclasses import dataclass
from typing import Optional, Callable, Any
import logging

# Transformers imports
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

LOGGER = logging.getLogger("base_agent")
LOGGER.setLevel(logging.INFO)
if not LOGGER.hasHandlers():
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s"))
    LOGGER.addHandler(h)


@dataclass
class SPARConfig:
    model_name: str = "Qwen/Qwen1.5-7B-Chat"
    use_trust_remote_code: bool = True
    device_map: str = "auto"
    torch_dtype: Optional[str] = "auto"  # "auto" -> will let transformers decide
    low_cpu_mem_usage: bool = True
    pipeline_task: str = "text-generation"
    max_new_tokens: int = 512
    temperature: float = 0.7


# Singleton manager for the model/pipeline
class LocalModelManager:
    _lock = threading.Lock()
    _tokenizer = None
    _model = None
    _pipeline = None
    _config = SPARConfig()

    @classmethod
    def get_config(cls) -> SPARConfig:
        return cls._config

    @classmethod
    def load_model(cls, force_reload: bool = False):
        with cls._lock:
            if cls._pipeline is not None and not force_reload:
                LOGGER.info("Model pipeline already loaded; reusing instance.")
                return cls._pipeline

            model_name = cls._config.model_name
            LOGGER.info(f"Loading model pipeline: {model_name}")

            # Safe loader with memory-friendly flags
            try:
                # Load tokenizer
                cls._tokenizer = AutoTokenizer.from_pretrained(
                    model_name, trust_remote_code=cls._config.use_trust_remote_code
                )

                # Load model
                cls._model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    trust_remote_code=cls._config.use_trust_remote_code,
                    device_map=cls._config.device_map,
                    low_cpu_mem_usage=cls._config.low_cpu_mem_usage,
                    torch_dtype=getattr(torch, cls._config.torch_dtype) if cls._config.torch_dtype and hasattr(torch, cls._config.torch_dtype) else None,
                )

                # Create pipeline
                cls._pipeline = pipeline(
                    cls._config.pipeline_task,
                    model=cls._model,
                    tokenizer=cls._tokenizer,
                )
                LOGGER.info("Model pipeline loaded successfully.")
                return cls._pipeline

            except Exception as e:
                LOGGER.exception("Failed to load model pipeline.")
                # Clean up partially loaded objects
                cls._tokenizer = None
                cls._model = None
                cls._pipeline = None
                raise

    @classmethod
    def get_pipeline(cls):
        if cls._pipeline is None:
            return cls.load_model()
        return cls._pipeline

    @classmethod
    def safe_reload(cls, new_model_name: Optional[str] = None):
        with cls._lock:
            if new_model_name:
                cls._config.model_name = new_model_name
            # delete references and reload
            cls._tokenizer = None
            cls._model = None
            cls._pipeline = None
            return cls.load_model()


# Small decorator helper for agent functions to standardize errors
def handle_errors(default_return: Any = None):
    def decorator(fn: Callable):
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                LOGGER.exception(f"Unhandled exception in {fn.__name__}")
                return default_return
        return wrapper
    return decorator
