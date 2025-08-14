import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
from app.modules import input_handler
import traceback
import asyncio
import json
from app.modules.orchestrator import orchestrate_dag
import requests

# Page configuration
st.set_page_config(
    page_title="spar.ai DSA LLM Assistant",
    layout="centered",
    initial_sidebar_state="auto"
)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'is_thinking' not in st.session_state:
    st.session_state.is_thinking = False
if 'sidebar_expanded' not in st.session_state:
    st.session_state.sidebar_expanded = True

st.markdown(
    """
    <style>
    body, .stApp {
        background: #18181b !important;
        color: #f3f4f6 !important;
    }
    .stSidebar {
        background: #23272f !important;
        border-radius: 0 18px 18px 0;
        box-shadow: 0 4px 32px 0 rgba(165, 180, 252, 0.10);
    }
    .sidebar-title {
        font-size: 1.5em;
        font-weight: 700;
        color: #a5b4fc;
        margin-bottom: 0.5em;
        margin-top: 0.5em;
    }
    .sidebar-history {
        margin-top: 2em;
        max-height: 60vh;
        overflow-y: auto;
        padding-right: 0.5em;
    }
    .sidebar-history-entry {
        background: rgba(39, 39, 42, 0.7);
        border-radius: 8px;
        margin-bottom: 0.5em;
        padding: 0.7em 1em;
        font-size: 1em;
        color: #f3f4f6;
        border-left: 3px solid #a5b4fc;
        transition: background 0.2s;
    }
    .sidebar-history-entry:hover {
        background: #2d2d36;
    }
    .section-header {
        display: none;
    }
    .stTextArea textarea {
        background: #232336 !important;
        color: #f3f4f6 !important;
        border-radius: 16px !important;
        font-size: 1.1em !important;
        font-family: 'Poppins', 'Inter', 'Segoe UI', Arial, sans-serif !important;
        box-shadow: 0 2px 12px 0 rgba(165, 180, 252, 0.10);
        border: 1.5px solid #35354a !important;
        padding: 1.2em 1.5em !important;
    }
    .stButton>button {
        background: linear-gradient(90deg,#a5b4fc,#fbc2eb);
        color: #232336;
        border-radius: 24px;
        font-weight: 700;
        font-size: 1.1em;
        border: none;
        padding: 0.7em 2.2em;
        margin-top: 0.5em;
        margin-bottom: 0.5em;
        box-shadow: 0 2px 12px 0 rgba(165, 180, 252, 0.10);
        transition: box-shadow 0.2s;
        outline: none !important;
    }
    .stButton>button:focus, .stButton>button:active {
        outline: none !important;
        border: none !important;
        box-shadow: none !important;
    }
    .stButton>button:hover {
        box-shadow: 0 4px 24px 0 rgba(165, 180, 252, 0.18);
        background: linear-gradient(90deg,#fbc2eb,#a5b4fc);
        outline: none !important;
        border: none !important;
    }
    .stJson, .stCode, .stAlert, .stMarkdown {
        border-radius: 16px !important;
        box-shadow: 0 2px 12px 0 rgba(165, 180, 252, 0.10);
        margin-bottom: 1.2em !important;
    }
    .explanation-box {
        background: #232336;
        color: #f3f4f6;
        border-radius: 12px;
        padding: 1.1em 1.3em;
        margin-bottom: 1em;
        font-weight: 500;
        box-shadow: 0 2px 8px 0 rgba(165, 180, 252, 0.07);
        border: 1px solid #35354a;
    }
    .subtask-box {
        background: #232336;
        color: #f3f4f6;
        border-radius: 12px;
        padding: 1.1em 1.3em;
        margin-bottom: 0.7em;
        font-weight: 500;
        box-shadow: 0 2px 8px 0 rgba(165, 180, 252, 0.07);
        border: 1px solid #35354a;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Sidebar: Task History ---
with st.sidebar:
    st.markdown('<div class="sidebar-title">Task History</div>', unsafe_allow_html=True)
    task_history = getattr(input_handler, "task_history", [])
    st.markdown('<div class="sidebar-history">', unsafe_allow_html=True)
    if task_history:
        for entry in reversed(task_history[-20:]):
            st.markdown(f'<div class="sidebar-history-entry">'
                        f'<b>{entry.get("language", "").capitalize()}</b> | '
                        f'{entry.get("original_prompt", "")[:40]}...'
                        f'<br><span style="font-size:0.9em;color:#a5b4fc;">{entry.get("timestamp", "")}</span>'
                        f'</div>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#888;">No history yet.</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- Main area title and subtitle ---
st.markdown('<div style="text-align:center;margin-top:2em;margin-bottom:0.5em;font-family:Inter,Segoe UI,Poppins,sans-serif;font-weight:800;font-size:3em;letter-spacing:0.01em;">SPAR</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center;margin-bottom:2.5em;font-family:Inter,Segoe UI,Poppins,sans-serif;font-weight:400;font-size:1.2em;color:#b3b3c6;">spar.ai: Agentic Code Reasoning Assistant</div>', unsafe_allow_html=True)

# --- Prompt input row: glassmorphism, centered, Cursor-style ---
col1, col2 = st.columns([8,1], gap="small")
with col1:
    prompt_text = st.text_area(
        "DSA Problem Input",  # Non-empty label for accessibility
        placeholder="enter your DSA problem...",
        key="prompt_input",
        height=68,
        label_visibility="collapsed",
        help=None,
        max_chars=None,
        disabled=False
    )
with col2:
    send_clicked = st.button(
        label="↑",  # Upward arrow for send, like Cursor UI
        key="send_btn",
        use_container_width=True,
        help="Send"
    )

# --- Custom CSS for font, glassmorphism, sidebar, and input ---
st.markdown(
    """
    <style>
    html, body, .stApp {
        background: #0a0a0a !important;
        color: #f3f4f6 !important;
        font-family: 'Inter', 'Segoe UI', 'Poppins', Arial, sans-serif !important;
    }
    .stSidebar {
        background: #18181b !important;
        border-radius: 0 18px 18px 0;
        box-shadow: 0 4px 32px 0 rgba(36,37,46,0.18);
    }
    .sidebar-title {
        font-size: 1.3em;
        font-weight: 700;
        color: #b3b3c6;
        margin-bottom: 0.5em;
        margin-top: 0.5em;
        letter-spacing: 0.01em;
    }
    .sidebar-history {
        margin-top: 2em;
        max-height: 60vh;
        overflow-y: auto;
        padding-right: 0.5em;
    }
    .sidebar-history-entry {
        background: rgba(36,37,46,0.7);
        border-radius: 8px;
        margin-bottom: 0.5em;
        padding: 0.7em 1em;
        font-size: 1em;
        color: #b3b3c6;
        border-left: 3px solid #35354a;
        transition: background 0.2s;
    }
    .sidebar-history-entry:hover {
        background: #232336;
    }
    .stTextArea textarea {
        background: rgba(36,37,46,0.7) !important;
        color: #b3b3c6 !important;
        border-radius: 18px !important;
        font-size: 1.2em !important;
        font-family: 'Inter', 'Segoe UI', 'Poppins', Arial, sans-serif !important;
        box-shadow: 0 2px 12px 0 rgba(36,37,46,0.10);
        border: 2px solid #a5b4fc !important;
        padding: 1.2em 1.5em !important;
    }
    .stButton>button {
        background: rgba(36,37,46,0.7);
        color: #b3b3c6;
        border-radius: 18px;
        font-weight: 700;
        font-size: 1.3em;
        border: none;
        padding: 0.7em 1.2em;
        margin-top: 0.5em;
        margin-bottom: 0.5em;
        box-shadow: 0 2px 12px 0 rgba(36,37,46,0.10);
        transition: box-shadow 0.2s;
        outline: none !important;
    }
    .stButton>button:focus, .stButton>button:active {
        outline: none !important;
        border: none !important;
        box-shadow: none !important;
    }
    .stButton>button:hover {
        box-shadow: 0 4px 24px 0 rgba(36,37,46,0.18);
        background: rgba(53,53,74,0.7);
        outline: none !important;
        border: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Centered output container below input row, same max width ---
if send_clicked and prompt_text.strip():
    user_input = input_handler.get_user_input(prompt_text, "python")
    print(f"[DEBUG] user_input dict: {user_input}")
    cleaned_prompt = user_input.get("cleaned_prompt", prompt_text)
    problem_text = cleaned_prompt
    st.session_state['last_prompt'] = cleaned_prompt
    st.session_state['last_task_history'] = input_handler.task_history

    st.markdown('<div style="display:flex;justify-content:center;width:100%;"><div style="max-width:650px;width:100%;margin:0 auto;">', unsafe_allow_html=True)
    
    try:
        lang = "python"

        # --- TUA Call ---
        with st.spinner("Running TaskUnderstandingAgent (TUA)..."):
            tua_response = requests.post(
                "http://localhost:8000/api/tua",
                json={"user_prompt": problem_text, "language": lang},
                timeout=60
            )
        tua_result = tua_response.json()

        if tua_response.status_code == 200:
            st.session_state["tua_output"] = tua_result
            method_used = tua_result.get('method_used', '')
            constraints = tua_result.get('constraints', '')
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>TaskUnderstandingAgent (TUA)</h4>", unsafe_allow_html=True)
            with st.expander("Structured Prompt"):
                st.code(tua_result.get("structured_prompt", ""), language="text")
            if method_used:
                st.markdown(f"<b>Method Used:</b> {method_used}", unsafe_allow_html=True)
            if constraints:
                st.markdown(f"<b>Constraints:</b> {constraints}", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error("TUA backend error")
            st.stop()

        # --- STD Call ---
        with st.spinner("Running SubtaskDistributor (STD)..."):
            std_response = requests.post(
                "http://localhost:8000/api/std",
                json={"structured_prompt": tua_result.get("structured_prompt", ""), "language": lang},
                timeout=60
            )
        std_result = std_response.json()

        if std_response.status_code == 200:
            std_data = std_result.get('std_result', {})
            st.session_state["std_output"] = std_data

            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>SubtaskDistributor (STD)</h4>", unsafe_allow_html=True)

            classification = std_data.get("classification", "UNKNOWN")
            if classification == "SIMPLE":
                st.success(f"**Classification: {classification}**")
            elif classification == "MEDIUM":
                st.warning(f"**Classification: {classification}**")
            elif classification == "COMPLEX":
                st.error(f"**Classification: {classification}**")
            else:
                st.info(f"**Classification: {classification}**")

            explanation = std_data.get("explanation", "")
            if explanation:
                st.markdown(f'<div class="glass-card" style="margin-bottom:1em;"><b>Explanation:</b><br>{explanation}</div>', unsafe_allow_html=True)

            subtasks = std_data.get("subtasks", [])
            if subtasks:
                st.markdown("**Subtasks:**")
                for subtask in subtasks:
                    st.markdown(
                        f"<div class=\"glass-card\" style=\"margin-bottom:1em;\"><b>{subtask.get('step','')}:</b> {subtask.get('description','')}</div>",
                        unsafe_allow_html=True
                    )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error("STD backend error")
            st.stop()

    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.info("If this persists, please contact support or check the backend logs.")
        st.code(traceback.format_exc(), language="python")
    st.markdown('</div></div>', unsafe_allow_html=True)

# --- PRA Integration ---
if st.session_state.get("tua_output") and st.session_state.get("std_output"):
    st.subheader("Prompt Refiner Agent Output")
    pra_input = {
        "tua": st.session_state["tua_output"],
        "std": st.session_state["std_output"]
    }
    try:
        pra_response = requests.post("http://localhost:8000/api/pra", json=pra_input).json()
        st.session_state["pra_output"] = pra_response
        
        if "refined_prompts" in pra_response:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>Prompt Refiner Agent (PRA)</h4>", unsafe_allow_html=True)
            
            refined_prompts = pra_response["refined_prompts"]
            if len(refined_prompts) == 1 and refined_prompts[0].get('subtask') == 'Complete Solution':
                refined_prompt = refined_prompts[0].get('refined_prompt', '')
                st.markdown("<b>Complete Solution:</b>", unsafe_allow_html=True)
                st.code(refined_prompt, language="text")
                st.session_state["refined_prompt"] = refined_prompt
            else:
                for item in refined_prompts:
                    subtask_label = item.get('subtask', 'Main Task')
                    refined_prompt = item.get('refined_prompt', '')
                    st.markdown(f"<b>{subtask_label}:</b>", unsafe_allow_html=True)
                    st.code(refined_prompt, language="text")
                    if 'refined_prompt' not in st.session_state:
                        st.session_state["refined_prompt"] = refined_prompt
            
            st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"PRA API failed: {str(e)}")

# --- Full Pipeline Execution: Broken into Modular Glass Cards ---
st.subheader("Code Generation & Testing Pipeline")

try:
    refined_prompt = st.session_state.get("refined_prompt", "")
    original_prompt = st.session_state.get('last_prompt', prompt_text)
    pipeline_prompt = refined_prompt if refined_prompt else original_prompt
    
    if refined_prompt:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-bottom:0.5em;'>Structured Prompt for Code Agent</h4>", unsafe_allow_html=True)
        st.code(refined_prompt, language="text")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with st.spinner("Running Code Generation → Testing → Debugging..."):
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
    
    if full_pipeline_response.status_code == 200:
        pipeline_result = full_pipeline_response.json()
        st.session_state["pipeline_result"] = pipeline_result
        
        # Code Generation Box
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-bottom:0.5em;'>Code Generation</h4>", unsafe_allow_html=True)
        code = pipeline_result.get("code", "")
        if code:
            st.code(code, language="python")
        else:
            st.warning("No code generated")
        code_source = pipeline_result.get("code_source", "unknown")
        st.markdown(f"**Source:** {code_source}", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Test Results Box
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-bottom:0.5em;'>Test Generation & Results</h4>", unsafe_allow_html=True)
        test_results = pipeline_result.get("test_results", {})
        if test_results:
            status = test_results.get("status", "unknown")
            passed = test_results.get("passed", 0)
            total = test_results.get("total", 0)
            if status == "pass":
                st.success(f"Tests Passed: {passed}/{total}")
            elif status == "fail":
                st.error(f"Tests Failed: {passed}/{total}")
                if "error" in test_results:
                    st.error(f"Error: {test_results['error']}")
            else:
                st.warning(f"Test Status: {status} ({passed}/{total})")
            
            test_cases = test_results.get("test_cases", [])
            if test_cases:
                st.markdown("**Test Cases:**")
                for i, test in enumerate(test_cases, 1):
                    st.code(test, language="python")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Self-Debug Box (only if tests failed and debug was triggered)
        if test_results.get("status") == "fail" and "debug_result" in pipeline_result:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>Self-Debug Agent</h4>", unsafe_allow_html=True)
            debug_result = pipeline_result["debug_result"]
            st.markdown(f"**Explanation:** {debug_result.get('debug_explanation', 'No explanation')}", unsafe_allow_html=True)
            fixed_code = debug_result.get('fixed_code', '')
            if fixed_code:
                st.markdown("**Fixed Code:**")
                st.code(fixed_code, language="python")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Timing Summary Box
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-bottom:0.5em;'>Timing Summary</h4>", unsafe_allow_html=True)
        code_time = pipeline_result.get("code_time", 0)
        test_time = pipeline_result.get("test_time", 0)
        total_time = pipeline_result.get("total_time", 0)
        st.markdown(f"- Code Generation: {code_time:.2f}s")
        st.markdown(f"- Testing/Debugging: {test_time:.2f}s")
        st.markdown(f"- Total Time: {total_time:.2f}s")
        st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        st.error("Pipeline failed")
        st.code(full_pipeline_response.text, language="text")

except Exception as e:
    st.error(f"Pipeline error: {str(e)}")
    st.info("Check backend logs.")

# CSS: Add glass-card, subtask-bubble, subtask-status for glassmorphic result cards and bubbles
st.markdown(
    """
    <style>
    .glass-card {
        background: rgba(36,37,46,0.7);
        backdrop-filter: blur(8px);
        border-radius: 1.5em;
        padding: 1.5em 1.7em;
        margin-bottom: 2em;
        box-shadow: 0 4px 32px 0 rgba(165,180,252,0.10);
        border: 1.5px solid #232336;
    }
    .subtask-bubble {
        display: inline-block;
        background: linear-gradient(90deg,#232336,#35354a);
        color: #b3b3c6;
        font-weight: 600;
        padding: 0.5em 1.1em;
        border-radius: 1.5em;
        font-size: 1.05em;
        margin: 0.3em 0.5em 0.3em 0;
        box-shadow: 0 2px 8px 0 rgba(165,180,252,0.07);
    }
    .subtask-status {
        margin-left: 0.7em;
        font-size: 0.95em;
        font-weight: 700;
        border-radius: 1em;
        padding: 0.2em 0.8em;
    }
    .subtask-pending {
        background: #fbbf24;
        color: #232336;
    }
    .subtask-complete {
        background: #22c55e;
        color: #fff;
    }
    </style>
    """,
    unsafe_allow_html=True
)