# app/model_manager.py
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch

logger = logging.getLogger("ModelManager")
if not logger.hasHandlers():
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s'))
    logger.addHandler(h)
logger.setLevel(logging.INFO)

# Configuration: change model_name if needed
MODEL_NAME = "Qwen/Qwen1.5-7B-Chat"

# global_pipeline will be the single shared pipeline instance
global_pipeline = None

def init_global_pipeline(device_map=None, max_new_tokens=512, trust_remote_code=True):
    global global_pipeline
    if global_pipeline is not None:
        logger.info("Model pipeline already loaded; reusing instance.")
        return global_pipeline

    logger.info(f"Loading model pipeline: {MODEL_NAME}")
    # Device selection
    device = 0 if torch.cuda.is_available() else -1
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=trust_remote_code)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if device == 0 else None,
            trust_remote_code=trust_remote_code
        )
        # Create text-generation pipeline
        global_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            device_map="auto" if device == 0 else None,
            trust_remote_code=trust_remote_code,
            max_new_tokens=max_new_tokens
        )
        logger.info("Model pipeline loaded successfully.")
    except Exception as e:
        logger.exception("Failed to load model pipeline")
        raise

    return global_pipeline

# initialize on import (safe: will only run once per process)
try:
    init_global_pipeline()
except Exception:
    # Let callers handle errors; keep global_pipeline as None if fail
    pass
