import os
import logging
import time
import gc
import torch
from dataclasses import dataclass
from functools import wraps
from typing import Optional, Union, List, Dict
from transformers import AutoTokenizer, AutoModelForCausalLM

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SPARConfig:
    """Configuration for SPAR system"""
    model_name: str = "Qwen/Qwen1.5-7B-Chat"
    device: str = "auto"  # Change to "cpu" for testing without GPU
    max_new_tokens: int = 512
    temperature: float = 0.3
    do_sample: bool = True
    top_p: float = 0.8
    test_timeout: int = 10
    max_test_cases: int = 5
    similarity_threshold: float = 0.8
    reuse_similar_code: bool = True

    @classmethod
    def from_env(cls):
        """Load configuration from environment variables"""
        return cls(
            model_name=os.getenv("MODEL_NAME", cls.model_name),
            device=os.getenv("DEVICE", cls.device),
            test_timeout=int(os.getenv("TEST_TIMEOUT", str(cls.test_timeout))),
            similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", str(cls.similarity_threshold)))
        )

def handle_errors(func):
    """Error handling decorator"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise
    return wrapper

class LocalModelManager:
    """Singleton manager for local model"""
    _instance = None
    _model = None
    _tokenizer = None
    _config = None
    _initialized = False
    _lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            import threading
            cls._lock = threading.Lock()
        return cls._instance

    @handle_errors
    def initialize(self, config: SPARConfig):
        """Initialize the local model"""
        with self._lock:
            if not self._initialized:
                logger.info(f"Loading model: {config.model_name}")
                
                # Set memory optimization environment variables
                os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
                
                # Clear any existing model from memory
                if self._model is not None:
                    del self._model
                    self._model = None
                if self._tokenizer is not None:
                    del self._tokenizer
                    self._tokenizer = None
                
                if torch.cuda.is_available() and config.device != "cpu":
                    torch.cuda.empty_cache()
                    gc.collect()
                
                self._tokenizer = AutoTokenizer.from_pretrained(
                    config.model_name,
                    trust_remote_code=True
                )
                
                device_map = "auto" if config.device == "auto" and torch.cuda.is_available() else None
                torch_dtype = torch.float16 if torch.cuda.is_available() and config.device != "cpu" else torch.float32
                
                # Add memory optimization settings with CPU offloading
                if config.device == "cpu":
                    # Force CPU-only
                    max_memory = None
                    device_map = None
                else:
                    if torch.cuda.is_available():
                        # 90% of total GPU memory in GB
                        gpu_total_mem = torch.cuda.get_device_properties(0).total_memory
                        gpu_mem_gb = int(gpu_total_mem / 1024**3 * 0.9)
                        max_memory = {0: f"{gpu_mem_gb}GB", "cpu": "32GB"}
                        device_map = "auto"
                    else:
                        max_memory = None
                        device_map = None

                
                self._model = AutoModelForCausalLM.from_pretrained(
                    config.model_name,
                    torch_dtype=torch_dtype,
                    device_map=device_map,
                    trust_remote_code=True,
                    low_cpu_mem_usage=True,
                    max_memory=max_memory,
                    offload_folder="offload"
                )
                
                self._config = config
                self._initialized = True
                logger.info("Model loaded successfully")
            
            return self._model, self._tokenizer

    @handle_errors
    def generate_content(self, prompt: Union[str, List[Dict[str, str]]], max_tokens: Optional[int] = None) -> str:
        """Generate content using the local model"""
        if self._model is None or self._tokenizer is None:
            logger.error("Model or tokenizer not initialized")
            raise RuntimeError("Model not initialized")
        
        max_tokens = max_tokens or self._config.max_new_tokens
        logger.info(f"Generating content with prompt length: {len(prompt)}")
        
        # Handle string or list of messages
        if isinstance(prompt, list):
            text = self._tokenizer.apply_chat_template(
                prompt,
                tokenize=False,
                add_generation_prompt=True
            )
        else:
            messages = [{"role": "user", "content": prompt}]
            text = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        
        model_inputs = self._tokenizer([text], return_tensors="pt").to(self._model.device)
        
        with torch.no_grad():
            generated_ids = self._model.generate(
                input_ids=model_inputs.input_ids,
                attention_mask=model_inputs.attention_mask,
                max_new_tokens=max_tokens,
                temperature=self._config.temperature,
                do_sample=self._config.do_sample,
                top_p=self._config.top_p,
                pad_token_id=self._tokenizer.eos_token_id
            )
        
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        
        response = self._tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        if torch.cuda.is_available() and self._config.device != "cpu":
            torch.cuda.empty_cache()
            gc.collect()
            for _ in range(3):
                gc.collect()
        
        logger.info(f"Generated response length: {len(response)}")
        return response.strip()

    def is_initialized(self) -> bool:
        """Check if model is initialized"""
        return self._model is not None and self._tokenizer is not None

    def clear_cache(self):
        """Clear GPU cache and memory"""
        if torch.cuda.is_available() and self._config.device != "cpu":
            torch.cuda.empty_cache()
        gc.collect()
        for _ in range(5):
            gc.collect()
        if hasattr(torch, 'cuda') and torch.cuda.is_available() and self._config.device != "cpu":
            torch.cuda.synchronize()