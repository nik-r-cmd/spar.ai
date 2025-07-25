from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import logging
import re

MODEL_NAME = "Qwen/Qwen1.5-7B-Chat"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype="auto",
    device_map="auto",
    trust_remote_code=True
)
llm_pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=512,
    do_sample=True,
    temperature=0.7,
)

class SubtaskDistributor:
    def __init__(self, llm_pipe):
        self.pipe = llm_pipe
        self.logger = logging.getLogger("SubtaskDistributor")
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _extract_assistant_response(self, full_output: str) -> str:
        """Extract only the assistant's response from the full conversation."""
        try:
            full_output = str(full_output)
            
            # Look for the assistant's response pattern
            assistant_pattern = r"'role': 'assistant', 'content': '([^']*)'"
            match = re.search(assistant_pattern, full_output)
            if match:
                return match.group(1)
            
            # Alternative pattern for different quote styles
            assistant_pattern2 = r"'role': 'assistant', 'content': \"([^\"]*)\""
            match = re.search(assistant_pattern2, full_output)
            if match:
                return match.group(1)
            
            # Fallback: look for content after the last assistant marker
            if "'role': 'assistant'" in full_output:
                parts = full_output.split("'role': 'assistant'")
                if len(parts) > 1:
                    last_part = parts[-1]
                    content_match = re.search(r"'content': '([^']*)'", last_part)
                    if content_match:
                        return content_match.group(1)
                    
                    content_match2 = re.search(r"'content': \"([^\"]*)\"", last_part)
                    if content_match2:
                        return content_match2.group(1)
            
            return full_output
            
        except Exception as e:
            self.logger.error(f"Error extracting assistant response: {e}")
            return str(full_output)

    def _clean_text(self, text: str) -> str:
        """Clean text by removing escape sequences and formatting properly."""
        if not text:
            return ""
        
        # Replace \n with actual newlines
        text = text.replace('\\n', '\n')
        # Remove extra whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        # Clean up leading/trailing whitespace
        text = text.strip()
        
        return text

    def _llm_prompt(self, structured_prompt: str) -> str:
        if self.pipe is None:
            self.logger.error("LLM pipe is not set. Cannot generate LLM response.")
            return "Error: LLM pipe is not available."
        prompt = [
            {
                "role": "system",
                "content": (
                    "You are an expert DSA problem classifier. "
                    "Classify problems as SIMPLE, MEDIUM, or COMPLEX, using the following human-like reasoning:\n"
                    "- SIMPLE: Direct, can be solved with basic loops/conditionals, no tricky edge cases, no advanced data structures, and the main idea is immediately clear. "
                    "Ignore any extra fluff or verbose description if the core logic is simple.\n"
                    "- MEDIUM: Needs a specific algorithm or data structure (e.g., binary search, sorting, basic tree/graph traversal), or has a few edge cases, or requires some non-trivial insight, but is not deeply layered or highly optimized.\n"
                    "- COMPLEX: Needs multiple algorithms, advanced data structures (e.g., segment trees, DP, complex graphs), many edge cases, or requires careful decomposition and planning. "
                    "If a human would need to pause and plan subtasks, or if the problem is likely to be >50 lines of code, it's COMPLEX.\n"
                    "Always reason as an expert teacher would, not just by code length or keywords."
                )
            },
            {
                "role": "user",
                "content": (
                    "Classify the following DSA problem as SIMPLE, MEDIUM, or COMPLEX.\n"
                    "Respond in this format:\n"
                    "Classification: <SIMPLE/MEDIUM/COMPLEX>\n"
                    "Explanation: <your reasoning>\n"
                    "If COMPLEX, also provide:\n"
                    "Subtasks:\n"
                    "Step 1: <description>\n"
                    "Step 2: <description>\n"
                    "...\n\n"
                    "DSA Problem:\n"
                    f"{structured_prompt}"
                )
            }
        ]
        self.logger.info("Prompting LLM for classification and decomposition...")
        
        try:
            outputs = self.pipe(prompt)
            
            # Extract the generated text
            if isinstance(outputs, list):
                if len(outputs) > 0 and isinstance(outputs[0], dict) and "generated_text" in outputs[0]:
                    result = outputs[0]["generated_text"]
                elif len(outputs) > 0 and isinstance(outputs[0], str):
                    result = outputs[0]
                else:
                    result = str(outputs[0])
            elif isinstance(outputs, dict) and "generated_text" in outputs:
                result = outputs["generated_text"]
            elif isinstance(outputs, str):
                result = outputs
            else:
                result = str(outputs)
            
            self.logger.info("LLM response received.")
            
            # Extract only the assistant's response
            clean_response = self._extract_assistant_response(result)
            self.logger.info(f"Cleaned response: {clean_response[:100]}...")
            
            return clean_response
            
        except Exception as e:
            self.logger.error(f"Error in LLM prompt: {e}")
            return f"Error generating response: {str(e)}"

    def __call__(self, input_dict):
        try:
            structured_prompt = input_dict.get("structured_prompt", "")
            if not structured_prompt:
                raise ValueError("Input must contain 'structured_prompt'.")
            if self.pipe is None:
                self.logger.error("LLM pipe is not set. Returning fallback error.")
                return {
                    "llm_response": "Error: LLM pipe is not available.",
                    "classification": "ERROR",
                    "explanation": "LLM pipe is not set. Cannot classify or decompose.",
                    "subtasks": None
                }
            llm_output = self._llm_prompt(structured_prompt)
            
            # Ensure llm_output is a string
            if not isinstance(llm_output, str):
                llm_output = str(llm_output)
            
            # Clean the text
            llm_output = self._clean_text(llm_output)
            
            # Parse the output
            classification = "UNKNOWN"
            explanation = ""
            subtasks = []
            
            # Extract classification
            class_match = re.search(r"Classification:\s*(SIMPLE|MEDIUM|COMPLEX)", llm_output, re.IGNORECASE)
            if class_match:
                classification = class_match.group(1).upper()
            
            # Extract explanation (stop at Subtasks:)
            explanation_match = re.search(r"Explanation:\s*(.*?)(?=\nSubtasks:|\Z)", llm_output, re.DOTALL | re.IGNORECASE)
            if explanation_match:
                explanation = explanation_match.group(1).strip()
                # Clean the explanation
                explanation = self._clean_text(explanation)
            
            # Extract subtasks (only from the Subtasks: section)
            if "Subtasks:" in llm_output:
                subtasks_section = llm_output.split("Subtasks:")[-1]
                # Look for Step patterns
                step_pattern = re.compile(r'Step\s+\d+:\s*(.*?)(?=\nStep\s+\d+:|$)', re.DOTALL | re.IGNORECASE)
                step_matches = step_pattern.findall(subtasks_section)
                
                for i, step_content in enumerate(step_matches, 1):
                    cleaned_step = self._clean_text(step_content)
                    subtasks.append({
                        "step": f"Step {i}",
                        "description": cleaned_step
                    })
            
            return {
                "llm_response": llm_output,
                "classification": classification,
                "explanation": explanation,
                "subtasks": subtasks if subtasks else None
            }
            
        except Exception as e:
            self.logger.error(f"Error in __call__: {e}")
            return {
                "llm_response": f"Error: {str(e)}",
                "classification": "ERROR",
                "explanation": f"An error occurred: {str(e)}",
                "subtasks": None
            }

# Singleton agent instance
agent = SubtaskDistributor(llm_pipe)

def run_subtask_distributor(structured_prompt: str):
    return agent({"structured_prompt": structured_prompt})