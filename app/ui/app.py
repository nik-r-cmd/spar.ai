import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
from app.modules import input_handler
import traceback
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

# --- Prompt input row ---
col1, col2 = st.columns([8,1], gap="small")
with col1:
    prompt_text = st.text_area(
        "DSA Problem Input",
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
        label="↑",
        key="send_btn",
        use_container_width=True,
        help="Send",
        args={"aria-label": "Submit DSA problem"}
    )

# --- Custom CSS for glassmorphism and UI polish ---
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
    .glass-card {
        background: rgba(36,37,46,0.7);
        backdrop-filter: blur(8px);
        border-radius: 1.5em;
        padding: 1.5em 1.7em;
        margin-bottom: 2em;
        box-shadow: 0 4px 32px 0 rgba(165,180,252,0.10);
        border: 1.5px solid #232336;
        transition: all 0.3s ease;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 40px 0 rgba(165,180,252,0.15);
    }
    .subtask-box {
        background: rgba(36,37,46,0.7);
        border-radius: 12px;
        padding: 1.1em 1.3em;
        margin-bottom: 0.7em;
        box-shadow: 0 2px 8px 0 rgba(165,180,252,0.07);
        border: 1px solid #35354a;
    }
    .subtask-status {
        margin-left: 0.7em;
        font-size: 0.95em;
        font-weight: 700;
        border-radius: 1em;
        padding: 0.2em 0.8em;
    }
    .subtask-complete {
        background: #22c55e;
        color: #fff;
    }
    .subtask-pending {
        background: #fbbf24;
        color: #232336;
    }
    .subtask-failed {
        background: #ef4444;
        color: #fff;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Handle Prompt Submission ---
if send_clicked and prompt_text.strip():
    user_input = input_handler.get_user_input(prompt_text, "python")
    cleaned_prompt = user_input.get("cleaned_prompt", prompt_text)
    st.session_state['last_prompt'] = cleaned_prompt
    st.session_state['last_task_history'] = input_handler.task_history
    st.session_state.tua_output = None
    st.session_state.std_output = None
    st.session_state.pra_output = None
    st.session_state.pipeline_result = None

    st.markdown('<div style="display:flex;justify-content:center;width:100%;"><div style="max-width:650px;width:100%;margin:0 auto;">', unsafe_allow_html=True)
    
    try:
        lang = "python"

        # --- TUA Call ---
        with st.spinner("Running Task Understanding Agent (TUA)..."):
            tua_response = requests.post(
                "http://localhost:8000/api/tua",
                json={"user_prompt": cleaned_prompt, "language": lang},
                timeout=60
            )
        if tua_response.status_code == 200:
            tua_result = tua_response.json()
            st.session_state.tua_output = tua_result
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>Task Understanding Agent (TUA) <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
            with st.expander("Structured Prompt"):
                st.code(tua_result.get("structured_prompt", ""), language="text")
            method_used = tua_result.get('method_used', '')
            constraints = tua_result.get('constraints', '')
            if method_used:
                st.markdown(f"<b>Method Used:</b> {method_used}", unsafe_allow_html=True)
            if constraints:
                st.markdown(f"<b>Constraints:</b> {constraints}", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error(f"TUA API failed with status {tua_response.status_code}: {tua_response.text}")
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>Task Understanding Agent (TUA) <span class='subtask-status subtask-failed'>Failed</span></h4>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()

        # --- STD Call ---
        with st.spinner("Running Subtask Distributor (STD)..."):
            std_response = requests.post(
                "http://localhost:8000/api/std",
                json={"structured_prompt": tua_result.get("structured_prompt", ""), "language": lang},
                timeout=60
            )
        if std_response.status_code == 200:
            std_result = std_response.json()
            st.session_state.std_output = std_result
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>Subtask Distributor (STD) <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
            classification = std_result.get("classification", "UNKNOWN")
            if classification == "SIMPLE":
                st.success(f"**Classification: {classification}**")
            elif classification == "MEDIUM":
                st.warning(f"**Classification: {classification}**")
            elif classification == "COMPLEX":
                st.error(f"**Classification: {classification}**")
            else:
                st.info(f"**Classification: {classification}**")
            explanation = std_result.get("explanation", "")
            if explanation:
                st.markdown(f'<div class="subtask-box"><b>Explanation:</b><br>{explanation}</div>', unsafe_allow_html=True)
            subtasks = std_result.get("subtasks", [])
            if subtasks:
                st.markdown("**Subtasks:**")
                for subtask in subtasks:
                    st.markdown(
                        f'<div class="subtask-box"><b>{subtask.get("step", "")}:</b> {subtask.get("description", "")}</div>',
                        unsafe_allow_html=True
                    )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error(f"STD API failed with status {std_response.status_code}: {std_response.text}")
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>Subtask Distributor (STD) <span class='subtask-status subtask-failed'>Failed</span></h4>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()

    except Exception as e:
        st.error(f"Error in TUA/STD execution: {str(e)}")
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(f"<h4 style='margin-bottom:0.5em;'>Pipeline Error <span class='subtask-status subtask-failed'>Failed</span></h4>", unsafe_allow_html=True)
        st.code(traceback.format_exc(), language="python")
        st.markdown('</div>', unsafe_allow_html=True)
        st.stop()
    st.markdown('</div></div>', unsafe_allow_html=True)

# --- PRA and Full Pipeline Execution ---
if st.session_state.get("tua_output") and st.session_state.get("std_output"):
    st.subheader("Code Generation & Testing Pipeline")
    st.markdown('<div style="display:flex;justify-content:center;width:100%;"><div style="max-width:650px;width:100%;margin:0 auto;">', unsafe_allow_html=True)
    
    try:
        # --- PRA Call ---
        with st.spinner("Running Prompt Refiner Agent (PRA)..."):
            pra_input = {
                "tua": st.session_state["tua_output"],
                "std": st.session_state["std_output"]
            }
            pra_response = requests.post("http://localhost:8000/api/pra", json=pra_input, timeout=60)
            if pra_response.status_code == 200:
                pra_result = pra_response.json()
                st.session_state.pra_output = pra_result
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown("<h4 style='margin-bottom:0.5em;'>Prompt Refiner Agent (PRA) <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
                refined_prompts = pra_result.get("refined_prompts", [])
                if refined_prompts:
                    if len(refined_prompts) == 1 and refined_prompts[0].get('subtask') == 'Complete Solution':
                        refined_prompt = refined_prompts[0].get('refined_prompt', '')
                        st.markdown("<b>Complete Solution:</b>", unsafe_allow_html=True)
                        with st.expander("Refined Prompt"):
                            st.code(refined_prompt, language="text")
                        st.session_state["refined_prompt"] = refined_prompt
                    else:
                        for item in refined_prompts:
                            subtask_label = item.get('subtask', 'Main Task')
                            refined_prompt = item.get('refined_prompt', '')
                            st.markdown(f"<b>{subtask_label}:</b>", unsafe_allow_html=True)
                            with st.expander(f"Refined Prompt for {subtask_label}"):
                                st.code(refined_prompt, language="text")
                            if 'refined_prompt' not in st.session_state:
                                st.session_state["refined_prompt"] = refined_prompt
                else:
                    st.warning("No refined prompts generated by PRA.")
                    st.markdown('<span class="subtask-status subtask-pending">Pending</span>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.error(f"PRA API failed with status {pra_response.status_code}: {pra_response.text}")
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown("<h4 style='margin-bottom:0.5em;'>Prompt Refiner Agent (PRA) <span class='subtask-status subtask-failed'>Failed</span></h4>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.stop()

        # --- Full Pipeline Execution ---
        refined_prompt = st.session_state.get("refined_prompt", "")
        original_prompt = st.session_state.get('last_prompt', prompt_text)
        pipeline_prompt = refined_prompt if refined_prompt else original_prompt

        if not pipeline_prompt:
            st.error("No valid prompt available for pipeline execution.")
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>Pipeline Error <span class='subtask-status subtask-failed'>Failed</span></h4>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()

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
            st.session_state.pipeline_result = pipeline_result

            # Structured Prompt Box
            if refined_prompt:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown("<h4 style='margin-bottom:0.5em;'>Structured Prompt for Code Agent <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
                with st.expander("Prompt Details"):
                    st.code(refined_prompt, language="text")
                st.markdown('</div>', unsafe_allow_html=True)

            # Code Generation Box
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>Code Generation <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
            code = pipeline_result.get("code", "")
            if code:
                with st.expander("Generated Code"):
                    st.code(code, language="python")
            else:
                st.warning("No code generated")
                st.markdown('<span class="subtask-status subtask-pending">Pending</span>', unsafe_allow_html=True)
            code_source = pipeline_result.get("code_source", "unknown")
            st.markdown(f"**Source:** {code_source}", unsafe_allow_html=True)
            if st.button("Export Code", key="export_code"):
                st.download_button("Download Code", code, file_name="solution.py")
            st.markdown('</div>', unsafe_allow_html=True)

            # Test Results Box
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            test_results = pipeline_result.get("test_results", {})
            status = test_results.get("status", "unknown")
            st.markdown(f"<h4 style='margin-bottom:0.5em;'>Test Generation & Results <span class='subtask-status {'subtask-complete' if status == 'pass' else 'subtask-failed'}> {'Passed' if status == 'pass' else 'Failed'}</span></h4>", unsafe_allow_html=True)
            if test_results:
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
                    with st.expander("Test Cases"):
                        for i, test in enumerate(test_cases, 1):
                            st.code(test, language="python")
                if st.button("Export Test Cases", key="export_tests"):
                    test_content = "\n".join(test_cases)
                    st.download_button("Download Tests", test_content, file_name="tests.py")
            else:
                st.warning("No test results available")
                st.markdown('<span class="subtask-status subtask-pending">Pending</span>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Self-Debug Box (only if tests failed and debug was triggered)
            if test_results.get("status") == "fail" and "debug_result" in pipeline_result:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown("<h4 style='margin-bottom:0.5em;'>Self-Debug Agent <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
                debug_result = pipeline_result["debug_result"]
                st.markdown(f"**Explanation:** {debug_result.get('debug_explanation', 'No explanation provided')}", unsafe_allow_html=True)
                fixed_code = debug_result.get('fixed_code', '')
                if fixed_code:
                    with st.expander("Fixed Code"):
                        st.code(fixed_code, language="python")
                    if st.button("Export Fixed Code", key="export_fixed_code"):
                        st.download_button("Download Fixed Code", fixed_code, file_name="fixed_solution.py")
                st.markdown('</div>', unsafe_allow_html=True)

            # Timing Summary Box
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>Timing Summary <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
            code_time = pipeline_result.get("code_time", 0)
            test_time = pipeline_result.get("test_time", 0)
            total_time = pipeline_result.get("total_time", 0)
            st.markdown(f"- Code Generation: {code_time:.2f}s")
            st.markdown(f"- Testing/Debugging: {test_time:.2f}s")
            st.markdown(f"- Total Time: {total_time:.2f}s")
            st.markdown('</div>', unsafe_allow_html=True)

        else:
            st.error(f"Full pipeline failed with status {full_pipeline_response.status_code}: {full_pipeline_response.text}")
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>Pipeline Error <span class='subtask-status subtask-failed'>Failed</span></h4>", unsafe_allow_html=True)
            st.code(full_pipeline_response.text, language="text")
            st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Pipeline error: {str(e)}")
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown(f"<h4 style='margin-bottom:0.5em;'>Pipeline Error <span class='subtask-status subtask-failed'>Failed</span></h4>", unsafe_allow_html=True)
        st.code(traceback.format_exc(), language="python")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div></div>', unsafe_allow_html=True)
else:
    if send_clicked and prompt_text.strip():
        st.warning("TUA or STD output missing. Please ensure the prompt is processed successfully.")
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-bottom:0.5em;'>Pipeline Error <span class='subtask-status subtask-pending'>Pending</span></h4>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    elif send_clicked:
        st.warning("Please enter a valid DSA problem prompt.")
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-bottom:0.5em;'>Input Error <span class='subtask-status subtask-pending'>Pending</span></h4>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)