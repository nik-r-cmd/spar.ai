# Full updated app.py with Method 1 Custom Input and fixes

import sys
import os
import html

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
from app.modules import input_handler
import traceback
import requests
import re
import time

# Page configuration
st.set_page_config(
    page_title="spar.ai DSA LLM Assistant",
    layout="wide",
    initial_sidebar_state="auto"
)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'is_thinking' not in st.session_state:
    st.session_state.is_thinking = False
if 'tua_output' not in st.session_state:
    st.session_state.tua_output = None
if 'std_output' not in st.session_state:
    st.session_state.std_output = None
if 'pra_output' not in st.session_state:
    st.session_state.pra_output = None
if 'pipeline_result' not in st.session_state:
    st.session_state.pipeline_result = None
if 'last_prompt' not in st.session_state:
    st.session_state.last_prompt = ""

# --- Sidebar: Task History ---
with st.sidebar:
    st.markdown('<div class="sidebar-title">Task History</div>', unsafe_allow_html=True)
    task_history = getattr(input_handler, "task_history", [])
    st.markdown('<div class="sidebar-history">', unsafe_allow_html=True)
    if task_history:
        for entry in reversed(task_history[-20:]):
            # Properly escape HTML content
            language = html.escape(entry.get("language", "").capitalize())
            prompt_preview = html.escape(entry.get("original_prompt", "")[:40] + "...")
            timestamp = html.escape(entry.get("timestamp", ""))
            st.markdown(f'<div class="sidebar-history-entry">'
                       f'<b>{language}</b> | {prompt_preview}'
                       f'<br><span style="font-size:0.9em;color:#1d9bf0;">{timestamp}</span>'
                       f'</div>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#aaaaaa;">No history yet.</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Updated CSS with glowing borders integrated into agent containers
st.markdown(
    """
    <style>
    html, body, .stApp {
        background: linear-gradient(to bottom, #000000, #0a0a0a) !important;
        color: #ffffff !important;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
    }

    .stSidebar {
        background: rgba(10,10,10,0.8) !important;
        backdrop-filter: blur(10px);
        border-radius: 0 20px 20px 0;
        box-shadow: 0 4px 32px rgba(29,155,240,0.15);
    }

    .sidebar-title {
        font-size: 1.4em;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.5em;
        margin-top: 0.5em;
        letter-spacing: 0.01em;
    }

    .sidebar-history {
        margin-top: 1em;
        max-height: 60vh;
        overflow-y: auto;
        padding-right: 0.5em;
    }

    .sidebar-history-entry {
        background: rgba(26,26,26,0.7);
        border-radius: 12px;
        margin-bottom: 0.8em;
        padding: 0.8em 1.2em;
        font-size: 1em;
        color: #dddddd;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(29,155,240,0.05);
    }

    .sidebar-history-entry:hover {
        background: rgba(26,26,26,0.9);
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(29,155,240,0.2);
    }

    /* Production-Ready Custom Input Styling - WIDER LENGTH */
    .custom-input-wrapper {
        position: relative;
        max-width: 90% !important;
        width: 90% !important;
        margin: 2em auto;
        display: block !important;
    }

    /* Completely hide native Streamlit input styling */
    .stTextInput {
        width: 100% !important;
        position: relative;
    }

    .stTextInput > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        height: 70px !important;
        position: relative !important;
        width: 100% !important;
    }

    .stTextInput > div > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        height: 70px !important;
        position: relative !important;
        width: 100% !important;
    }

    .stTextInput > div > div > input {
        background: rgba(10,10,10,0.8) !important;
        color: #ffffff !important;
        border-radius: 35px !important;
        font-size: 1.3em !important;
        box-shadow: 0 4px 16px rgba(29,155,240,0.1), inset 0 0 10px rgba(29,155,240,0.2) !important;
        border: 1px solid rgba(29,155,240,0.3) !important;
        padding: 0 90px 0 2.5em !important;
        height: 70px !important;
        width: 100% !important;
        transition: all 0.3s ease, box-shadow 0.5s ease !important;
        font-family: inherit !important;
        line-height: normal !important;
        box-sizing: border-box !important;
        backdrop-filter: blur(20px) !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #1d9bf0 !important;
        box-shadow: 0 4px 16px rgba(29,155,240,0.2), inset 0 0 15px rgba(29,155,240,0.4) !important;
        outline: none !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: rgba(255,255,255,0.6) !important;
    }

    /* Hide the label completely */
    .stTextInput > label {
        display: none !important;
    }

    /* Position submit button INSIDE the input field */
    .stFormSubmitButton {
        position: absolute !important;
        right: 5px !important;
        top: 5px !important;
        z-index: 1000 !important;
        height: 60px !important;
        width: 60px !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #1d9bf0, #0a84ff) !important;
        color: #ffffff !important;
        border-radius: 50% !important;
        font-weight: 700 !important;
        font-size: 1.6em !important;
        border: none !important;
        width: 60px !important;
        height: 60px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 16px rgba(29,155,240,0.3) !important;
        transition: all 0.3s ease !important;
        cursor: pointer !important;
        margin: 0 !important;
        padding: 0 !important;
        min-width: unset !important;
        min-height: unset !important;
    }

    .stFormSubmitButton > button:hover {
        box-shadow: 0 6px 24px rgba(29,155,240,0.4) !important;
        transform: translateY(-2px) !important;
        background: linear-gradient(135deg, #2aa3f0, #1a94ff) !important;
    }

    .stFormSubmitButton > button:active {
        transform: translateY(0px) !important;
    }

    .stFormSubmitButton > button:focus {
        box-shadow: 0 6px 24px rgba(29,155,240,0.4) !important;
        outline: none !important;
    }

    /* Form container adjustments */
    .stForm {
        background: transparent !important;
        border: none !important;
        width: 100% !important;
        position: relative !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    .stForm > div {
        display: block !important;
        position: relative !important;
        width: 100% !important;
    }

    /* Hide any remaining Streamlit artifacts */
    div[data-testid="stForm"] {
        background: transparent !important;
        border: none !important;
    }

    div[data-testid="stForm"] > div {
        background: transparent !important;
        border: none !important;
    }

    /* UPDATED Agent container styling - WITH INTEGRATED GLOWY BORDER */
    .agent-container {
        position: relative;
        background: rgba(10,10,10,0.6);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 2em;
        margin-bottom: 2.5em;
        overflow: hidden;
        transition: all 0.3s ease;
    }

    /* Glowing border effect using pseudo-elements */
    .agent-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(135deg, #1d9bf0, #00a8ff, #0078d4);
        border-radius: 20px;
        padding: 2px;
        z-index: 1;
        mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        mask-composite: xor;
        -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
    }

    /* Glowing shadow effect */
    .agent-container::after {
        content: '';
        position: absolute;
        top: -4px;
        left: -4px;
        right: -4px;
        bottom: -4px;
        background: linear-gradient(135deg, #1d9bf0, #00a8ff, #0078d4);
        border-radius: 24px;
        z-index: -1;
        filter: blur(12px);
        opacity: 0.4;
        transition: all 0.3s ease;
    }

    /* Content layer */
    .agent-container > * {
        position: relative;
        z-index: 2;
    }

    /* Hover effects */
    .agent-container:hover::after {
        opacity: 0.7;
        filter: blur(16px);
    }

    .agent-container:hover {
        transform: translateY(-2px);
    }

    /* Animation for active states */
    @keyframes glow-pulse {
        0%, 100% { opacity: 0.4; }
        50% { opacity: 0.8; }
    }

    .agent-container.active::after {
        animation: glow-pulse 2s ease-in-out infinite;
    }

    /* Different colors for different agent states */
    .agent-container.completed::before,
    .agent-container.completed::after {
        background: linear-gradient(135deg, #1d9bf0, #00a8ff, #0078d4);
    }

    .agent-container.running::before,
    .agent-container.running::after {
        background: linear-gradient(135deg, #ffa500, #ff8c00, #ff6b00);
    }

    .agent-container.failed::before,
    .agent-container.failed::after {
        background: linear-gradient(135deg, #ef4444, #dc2626, #b91c1c);
    }

    .subtask-box {
        background: rgba(26,26,26,0.7);
        border-radius: 12px;
        padding: 1.2em;
        margin-bottom: 1em;
        box-shadow: 0 2px 8px rgba(29,155,240,0.05);
        border: 1px solid rgba(29,155,240,0.1);
        transition: all 0.3s ease;
    }

    .subtask-status {
        margin-left: 0.8em;
        font-size: 1em;
        font-weight: 700;
        border-radius: 1.2em;
        padding: 0.3em 1em;
        transition: all 0.3s ease;
    }

    .subtask-complete {
        background: linear-gradient(135deg, #1d9bf0, #0a84ff);
        color: #ffffff;
    }

    .subtask-pending {
        background: #fbbf24;
        color: #000000;
    }

    .subtask-failed {
        background: #ef4444;
        color: #ffffff;
    }

    .test-bubble {
        background: rgba(26,26,26,0.7);
        border-radius: 16px;
        padding: 1em;
        margin-bottom: 1em;
        display: flex;
        align-items: center;
        box-shadow: 0 2px 8px rgba(29,155,240,0.05);
        border: 1px solid rgba(29,155,240,0.1);
        transition: all 0.3s ease;
    }

    .test-bubble:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(29,155,240,0.15);
    }

    .test-pass {
        background: rgba(0,200,0,0.1);
        border-color: #00c800;
    }

    .test-fail {
        background: rgba(255,0,0,0.1);
        border-color: #ff0000;
    }

    .test-icon {
        font-size: 1.5em;
        margin-right: 1em;
    }

    /* Main title - production optimized */
    .main-title {
        text-align: center;
        margin-top: 0.5em;
        margin-bottom: 1.5em;
        font-family: 'Inter', sans-serif;
        font-weight: 900;
        font-size: 8em !important;
        letter-spacing: -0.05em;
        color: #ffffff;
        text-shadow: 0 0 30px rgba(255, 255, 255, 0.8), 0 0 60px rgba(29, 155, 240, 0.6);
        animation: glow-pulse-title 2s ease-in-out infinite alternate;
    }

    @keyframes glow-pulse-title {
        from { text-shadow: 0 0 20px rgba(255, 255, 255, 0.6), 0 0 40px rgba(29, 155, 240, 0.4); }
        to { text-shadow: 0 0 40px rgba(255, 255, 255, 1), 0 0 80px rgba(29, 155, 240, 0.8); }
    }

    /* Responsive design for production */
    @media (max-width: 1200px) {
        .main-title {
            font-size: 12em !important;
        }
    }

    @media (max-width: 768px) {
        .main-title {
            font-size: 8em !important;
        }
        .custom-input-wrapper {
            margin: 1.5em auto;
            max-width: 95% !important;
            width: 95% !important;
        }
        .stTextInput > div > div > input {
            padding: 0 80px 0 1.5em !important;
            font-size: 1.1em !important;
            height: 60px !important;
        }
        .stTextInput > div {
            height: 60px !important;
        }
        .stTextInput > div > div {
            height: 60px !important;
        }
        .stFormSubmitButton {
            width: 50px !important;
            height: 50px !important;
            right: 5px !important;
            top: 5px !important;
        }
        .stFormSubmitButton > button {
            width: 50px !important;
            height: 50px !important;
            font-size: 1.4em !important;
        }
        .agent-container {
            padding: 1.5em;
            margin-bottom: 2em;
        }
    }

    @media (max-width: 480px) {
        .main-title {
            font-size: 5em !important;
        }
        .custom-input-wrapper {
            max-width: 98% !important;
            width: 98% !important;
        }
        .stTextInput > div > div > input {
            height: 55px !important;
            font-size: 1em !important;
            padding: 0 70px 0 1.2em !important;
        }
        .stTextInput > div {
            height: 55px !important;
        }
        .stTextInput > div > div {
            height: 55px !important;
        }
        .stFormSubmitButton {
            width: 45px !important;
            height: 45px !important;
            top: 5px !important;
        }
        .stFormSubmitButton > button {
            width: 45px !important;
            height: 45px !important;
            font-size: 1.2em !important;
        }
    }

    /* Loading states for production */
    .stSpinner > div {
        border-color: #1d9bf0 transparent #1d9bf0 transparent !important;
    }

    /* Fix any Streamlit layout issues */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }

    /* Ensure proper z-indexing */
    .stApp > header {
        background: transparent !important;
    }

    /* Performance optimizations */
    * {
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Main Title - Much Larger ---
st.markdown('<h1 class="main-title">spar.ai</h1>', unsafe_allow_html=True)

# --- Fixed Custom Input with Form ---
st.markdown('<div class="custom-input-wrapper">', unsafe_allow_html=True)
with st.form(key="custom_prompt_form", clear_on_submit=True):
    col1, col2 = st.columns([9, 1])
    with col1:
        user_input = st.text_input(
            "",
            placeholder="Ask Anything...",
            label_visibility="collapsed",
            key="main_input"
        )
    with col2:
        submitted = st.form_submit_button("↑")
st.markdown('</div>', unsafe_allow_html=True)

# --- Handle Prompt Submission ---
if submitted and user_input.strip():
    # Clean and prepare the input
    cleaned_input = user_input.strip()
    user_data = input_handler.get_user_input(cleaned_input, "python")
    cleaned_prompt = user_data.get("cleaned_prompt", cleaned_input)
    st.session_state['last_prompt'] = cleaned_prompt
    
    # Reset previous outputs
    st.session_state.tua_output = None
    st.session_state.std_output = None
    st.session_state.pra_output = None
    st.session_state.pipeline_result = None
    
    # Container for results
    st.markdown('<div style="display:flex;justify-content:center;width:100%;"><div style="max-width:800px;width:100%;margin:0 auto;">', unsafe_allow_html=True)
    
    try:
        lang = "python"
        overall_start = time.time()
        
        # --- TUA Call ---
        with st.spinner("Running Task Understanding Agent (TUA)..."):
            tua_start = time.time()
            try:
                tua_response = requests.post(
                    "http://localhost:8000/api/tua",
                    json={"user_prompt": cleaned_prompt, "language": lang},
                    timeout=60
                )
                tua_time = time.time() - tua_start
                
                if tua_response.status_code == 200:
                    tua_result = tua_response.json()
                    st.session_state.tua_output = tua_result
                    
                    st.markdown('<div class="agent-container completed">', unsafe_allow_html=True)
                    st.markdown("<h4 style='margin-bottom:0.5em;'>Task Understanding Agent (TUA) <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
                    
                    with st.expander("Structured Prompt"):
                        st.code(tua_result.get("structured_prompt", ""), language="text")
                    
                    method_used = html.escape(tua_result.get('method_used', ''))
                    constraints = html.escape(tua_result.get('constraints', ''))
                    if method_used:
                        st.markdown(f"<b>Method Used:</b> {method_used}", unsafe_allow_html=True)
                    if constraints:
                        st.markdown(f"<b>Constraints:</b> {constraints}", unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.error(f"TUA API failed with status {tua_response.status_code}")
                    st.stop()
            except requests.exceptions.RequestException as e:
                st.error(f"TUA API connection failed: {str(e)}")
                st.stop()

        # --- STD Call ---
        with st.spinner("Running Subtask Distributor (STD)..."):
            std_start = time.time()
            try:
                std_response = requests.post(
                    "http://localhost:8000/api/std",
                    json={"structured_prompt": tua_result.get("structured_prompt", ""), "language": lang},
                    timeout=60
                )
                std_time = time.time() - std_start
                
                if std_response.status_code == 200:
                    std_result = std_response.json()
                    std_data = std_result.get('std_result', std_result)
                    st.session_state.std_output = std_data
                    
                    st.markdown('<div class="agent-container completed">', unsafe_allow_html=True)
                    st.markdown("<h4 style='margin-bottom:0.5em;'>Subtask Distributor (STD) <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
                    
                    classification = std_data.get("classification", "UNKNOWN")
                    if classification == "SIMPLE":
                        st.success(f"**Classification: {classification}**")
                    elif classification == "COMPLEX":
                        st.error(f"**Classification: {classification}**")
                    else:
                        st.info(f"**Classification: {classification}**")
                    
                    explanation = std_data.get("explanation", "")
                    if explanation:
                        safe_explanation = html.escape(explanation)
                        st.markdown(f'<div class="subtask-box"><b>Explanation:</b><br>{safe_explanation}</div>', unsafe_allow_html=True)
                    
                    subtasks = std_data.get("subtasks", None)
                    if subtasks is None:
                        # Parse from llm_response if None
                        llm_resp = std_data.get("llm_response", "")
                        subtasks_match = re.search(r'Subtasks:\s*(.*)', llm_resp, re.DOTALL)
                        if subtasks_match:
                            subtasks_text = subtasks_match.group(1).strip().split('\n')
                            subtasks = [{'step': i+1, 'description': s.strip('* ').strip()}
                                       for i, s in enumerate(subtasks_text) if s.strip()]
                    
                    if subtasks and classification != "SIMPLE":
                        st.markdown("**Subtasks:**")
                        for subtask in subtasks:
                            safe_desc = html.escape(subtask.get("description", ""))
                            st.markdown(
                                f'<div class="subtask-box"><b>{subtask.get("step", "")}:</b> {safe_desc}</div>',
                                unsafe_allow_html=True
                            )
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.error(f"STD API failed with status {std_response.status_code}")
                    st.stop()
            except requests.exceptions.RequestException as e:
                st.error(f"STD API connection failed: {str(e)}")
                st.stop()

        # --- PRA Call ---
        with st.spinner("Running Prompt Refiner Agent (PRA)..."):
            pra_start = time.time()
            try:
                pra_input = {
                    "tua": st.session_state["tua_output"],
                    "std": st.session_state["std_output"]
                }
                pra_response = requests.post("http://localhost:8000/api/pra", json=pra_input, timeout=60)
                pra_time = time.time() - pra_start
                
                if pra_response.status_code == 200:
                    pra_result = pra_response.json()
                    st.session_state.pra_output = pra_result
                    
                    st.markdown('<div class="agent-container completed">', unsafe_allow_html=True)
                    st.markdown("<h4 style='margin-bottom:0.5em;'>Prompt Refiner Agent (PRA) <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
                    
                    refined_prompts = pra_result.get("refined_prompts", [])
                    if refined_prompts:
                        if len(refined_prompts) == 1 and refined_prompts[0].get('subtask') == 'Complete Solution':
                            st.markdown("<b>Complete Solution Refined:</b>", unsafe_allow_html=True)
                            st.code(refined_prompts[0].get('refined_prompt', ''), language="text")
                        else:
                            for item in refined_prompts:
                                subtask_label = html.escape(item.get('subtask', 'Main Task'))
                                st.markdown(f"<b>{subtask_label}:</b>", unsafe_allow_html=True)
                                st.code(item.get('refined_prompt', ''), language="text")
                    else:
                        st.warning("No refined prompts generated by PRA.")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.error(f"PRA API failed with status {pra_response.status_code}")
                    st.stop()
            except requests.exceptions.RequestException as e:
                st.error(f"PRA API connection failed: {str(e)}")
                st.stop()

        # --- Full Pipeline Execution ---
        original_prompt = st.session_state.get('last_prompt', cleaned_prompt)
        
        # Get refined prompt from PRA output
        refined_prompt = ""
        if st.session_state.pra_output:
            refined_prompts = st.session_state.pra_output.get("refined_prompts", [])
            if refined_prompts:
                refined_prompt = refined_prompts[0].get('refined_prompt', '')
        
        if not original_prompt:
            st.error("No valid prompt available for pipeline execution.")
            st.stop()
        
        with st.spinner("Running Code Agent → Tester Agent → SelfDebugger (if needed)..."):
            pipeline_start = time.time()
            try:
                full_pipeline_response = requests.post(
                    "http://localhost:8000/api/full-pipeline",
                    json={
                        "user_prompt": original_prompt,
                        "language": "python",
                        "refined_prompt": refined_prompt,
                        "signature": st.session_state["tua_output"].get("signature", "def solution(*args, **kwargs):"),
                        "edge_cases": st.session_state["tua_output"].get("edge_cases", "Handle all relevant edge cases")
                    },
                    timeout=300
                )
                pipeline_time = time.time() - pipeline_start
                
                if full_pipeline_response.status_code == 200:
                    pipeline_result = full_pipeline_response.json()
                    st.session_state.pipeline_result = pipeline_result
                    
                    # Code Agent Card
                    st.markdown('<div class="agent-container completed">', unsafe_allow_html=True)
                    st.markdown("<h4 style='margin-bottom:0.5em;'>Code Agent <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
                    
                    code = pipeline_result.get("code", "")
                    if code:
                        with st.expander("Generated Code"):
                            st.code(code, language="python")
                        
                        if "sub_codes" in pipeline_result:
                            with st.expander("Subtask Codes (for Complex Tasks)"):
                                for i, sub_code in enumerate(pipeline_result["sub_codes"]):
                                    st.markdown(f"**Subtask {i+1}:**")
                                    st.code(sub_code, language="python")
                    else:
                        st.warning("No code generated")
                    
                    code_source = html.escape(pipeline_result.get("code_source", "unknown"))
                    st.markdown(f"**Source:** {code_source}", unsafe_allow_html=True)
                    
                    if code and st.button("Export Code", key="export_code"):
                        st.download_button("Download Code", code, file_name="solution.py")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Tester Agent Card
                    st.markdown('<div class="agent-container completed">', unsafe_allow_html=True)
                    test_results = pipeline_result.get("test_results", {})
                    status = test_results.get("status", "unknown")
                    status_class = 'subtask-complete' if status == 'pass' else 'subtask-failed'
                    status_text = 'Passed' if status == 'pass' else 'Failed'
                    
                    st.markdown(f"<h4 style='margin-bottom:0.5em;'>Tester Agent <span class='subtask-status {status_class}'>{status_text}</span></h4>", unsafe_allow_html=True)
                    
                    if test_results:
                        passed = test_results.get("passed", 0)
                        total = test_results.get("total", 0)
                        if status == "pass":
                            st.success(f"Tests Passed: {passed}/{total}")
                        elif status == "fail":
                            st.error(f"Tests Passed: {passed}/{total}")
                        else:
                            st.warning(f"Test Status: {status} ({passed}/{total})")
                        
                        if "error" in test_results:
                            safe_error = html.escape(test_results["error"])
                            st.error(f"Overall Error: {safe_error}")
                        
                        detailed_results = test_results.get("detailed_test_results", [])
                        if detailed_results:
                            st.markdown("**Test Cases:**")
                            for res in detailed_results:
                                test_class = "test-pass" if res["status"] == "pass" else "test-fail"
                                icon = "✅" if res["status"] == "pass" else "❌"
                                safe_test = html.escape(res.get("test", ""))
                                error_html = ""
                                if 'error' in res:
                                    safe_error = html.escape(res['error'])
                                    error_html = f"<br><span style=\"color:#ff0000;\">Error: {safe_error}</span>"
                                
                                st.markdown(f'<div class="test-bubble {test_class}">'
                                           f'<span class="test-icon">{icon}</span>'
                                           f'<code>{safe_test}</code>'
                                           f'{error_html}'
                                           f'</div>', unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # SelfDebugger Card (if debugged)
                    if "debug_explanation" in pipeline_result:
                        st.markdown('<div class="agent-container completed">', unsafe_allow_html=True)
                        st.markdown("<h4 style='margin-bottom:0.5em;'>SelfDebugger Agent <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
                        
                        safe_explanation = html.escape(pipeline_result.get('debug_explanation', ''))
                        st.markdown(f"<b>Explanation:</b> {safe_explanation}", unsafe_allow_html=True)
                        
                        with st.expander("Fixed Code"):
                            st.code(pipeline_result["code"], language="python")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Timing Summary
                    total_time = time.time() - overall_start
                    st.markdown('<div class="agent-container completed">', unsafe_allow_html=True)
                    st.markdown("<h4 style='margin-bottom:0.5em;'>Timing Summary <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
                    st.markdown(f"- TUA: {tua_time:.2f}s")
                    st.markdown(f"- STD: {std_time:.2f}s")
                    st.markdown(f"- PRA: {pra_time:.2f}s")
                    st.markdown(f"- Pipeline (Code/Test/Debug): {pipeline_time:.2f}s")
                    st.markdown(f"- **Total Time: {total_time:.2f}s**")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                else:
                    st.error(f"Pipeline API failed with status {full_pipeline_response.status_code}")
            except requests.exceptions.RequestException as e:
                st.error(f"Pipeline API connection failed: {str(e)}")
            except Exception as e:
                st.error(f"Error in execution: {str(e)}")
                st.markdown('<div class="agent-container failed">', unsafe_allow_html=True)
                st.markdown("<h4 style='margin-bottom:0.5em;'>Pipeline Error <span class='subtask-status subtask-failed'>Failed</span></h4>", unsafe_allow_html=True)
                st.code(traceback.format_exc(), language="python")
                st.markdown('</div>', unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"Overall execution error: {str(e)}")
        st.markdown('<div class="agent-container failed">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-bottom:0.5em;'>Overall Error <span class='subtask-status subtask-failed'>Failed</span></h4>", unsafe_allow_html=True)
        st.code(traceback.format_exc(), language="python")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div></div>', unsafe_allow_html=True)