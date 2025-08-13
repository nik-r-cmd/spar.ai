# app/model_manager.py
"""
Global model pipeline manager (singleton + lazy load).
This ensures a single shared pipeline instance per process, and avoids eager loading at import time.
"""

import threading
import logging
from typing import Optional

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

logger = logging.getLogger("model_manager")
if not logger.hasHandlers():
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s'))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

_MODEL_NAME = "Qwen/Qwen1.5-7B-Chat"
_max_new_tokens_default = 512

_lock = threading.Lock()
_pipeline = None  # shared pipeline instance


def get_pipeline(max_new_tokens: Optional[int] = None, trust_remote_code: bool = True):
    """
    Lazily initialize and return the shared Hugging Face pipeline.
    Safe to call from multiple agents; initialization is guarded by a lock.
    """
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    with _lock:
        if _pipeline is not None:
            return _pipeline

        model_name = _MODEL_NAME
        logger.info(f"Loading model pipeline: {model_name}")

        try:
            device_is_cuda = torch.cuda.is_available()
            torch_dtype = torch.float16 if device_is_cuda else torch.float32
            device_map = "auto" if device_is_cuda else None

            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=trust_remote_code)

            # from_pretrained with device_map (lets accelerate / transformers place tensors on GPU)
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=trust_remote_code,
                device_map=device_map,
                low_cpu_mem_usage=True,
                torch_dtype=torch_dtype,
            )

            _pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
            )

            # set default generation param on pipeline if needed (but we'll pass explicit args when calling)
            logger.info("Model pipeline loaded successfully.")
            return _pipeline

        except Exception:
            logger.exception("Failed to load model pipeline")
            # leave _pipeline as None for callers to handle
            raise


def safe_reload(new_model_name: Optional[str] = None):
    """
    Clear and reload the global pipeline. Use with caution during development.
    """
    global _pipeline, _MODEL_NAME
    with _lock:
        if new_model_name:
            _MODEL_NAME = new_model_name
        _pipeline = None
        return get_pipeline()
