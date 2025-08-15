# Full updated app.py with fixes and improvements
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
import re  # For parsing subtasks if needed
import time  # For timing

# Page configuration
st.set_page_config(
    page_title="spar.ai DSA LLM Assistant",
    layout="wide",  # Wider for fluid feel
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
                        f'<br><span style="font-size:0.9em;color:#1d9bf0;">{entry.get("timestamp", "")}</span>'
                        f'</div>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#aaaaaa;">No history yet.</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- Custom Typography and Prompt Box with Integrated Send Button ---
# Using advanced HTML/CSS/JS for KIMI-like UI, Streamlit-compatible via st.components.v1.html
st.components.v1.html("""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@900&display=swap'); /* Bold typography font */
    .kimi-title {
      text-align: center;
      margin-top: 1em;
      margin-bottom: 0.5em;
      font-family: 'Inter', sans-serif;
      font-weight: 900;
      font-size: 6em;
      letter-spacing: -0.05em;
      color: #ffffff;
      text-shadow: 0 0 20px rgba(255, 255, 255, 0.5), 0 0 40px rgba(29, 155, 240, 0.3); /* Glowing effect */
      animation: glow-pulse 2s ease-in-out infinite alternate;
    }
    @keyframes glow-pulse {
      from { text-shadow: 0 0 10px rgba(255, 255, 255, 0.3), 0 0 20px rgba(29, 155, 240, 0.2); }
      to { text-shadow: 0 0 30px rgba(255, 255, 255, 0.7), 0 0 60px rgba(29, 155, 240, 0.5); }
    }
    .kimi-subtitle {
      text-align: center;
      margin-bottom: 1.5em;
      font-weight: 400;
      font-size: 1.2em;
      color: #aaaaaa;
    }
    .kimi-prompt-container {
      position: relative;
      max-width: 800px;
      margin: 0 auto;
      display: flex;
      justify-content: center;
    }
    .kimi-prompt {
      background: rgba(10,10,10,0.8);
      color: #ffffff;
      border-radius: 30px;
      font-size: 1.2em;
      box-shadow: 0 4px 16px rgba(29,155,240,0.1), inset 0 0 10px rgba(29,155,240,0.2); /* Inner glow */
      border: 1px solid rgba(29,155,240,0.3);
      padding: 1.2em 3em 1.2em 1.5em;
      width: 100%;
      min-height: 68px;
      resize: vertical;
      transition: all 0.3s ease, box-shadow 0.5s ease;
    }
    .kimi-prompt:focus {
      border-color: #1d9bf0;
      box-shadow: 0 4px 16px rgba(29,155,240,0.2), inset 0 0 15px rgba(29,155,240,0.4); /* Enhanced glow on focus */
      outline: none;
    }
    .kimi-send-btn {
      position: absolute;
      right: 1em;
      top: 50%;
      transform: translateY(-50%);
      background: linear-gradient(135deg, #1d9bf0, #0a84ff);
      color: #ffffff;
      border-radius: 50%;
      font-weight: 700;
      font-size: 1.2em;
      border: none;
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 16px rgba(29,155,240,0.3);
      transition: all 0.3s ease;
      cursor: pointer;
    }
    .kimi-send-btn:hover {
      box-shadow: 0 6px 24px rgba(29,155,240,0.4);
      transform: translateY(-52%);
    }
  </style>
  <script>
    function sendPrompt() {
      // JS to simulate send, but in Streamlit, we'll handle via button click
      document.getElementById('kimi-prompt').value = '';
    }
  </script>
</head>
<body>
  <div class="kimi-title">spar.ai</div>
  <div class="kimi-prompt-container">
    <textarea id="kimi-prompt" class="kimi-prompt" placeholder="Ask Anything..."></textarea>
    <button class="kimi-send-btn" onclick="sendPrompt()">↑</button>
  </div>
</body>
</html>
""", height=300, scrolling=False)  # Height adjusted for title and prompt box

# Note: Since Streamlit doesn't support direct JS interaction for button clicks in HTML, we'll keep the original prompt_text and send_clicked for functionality
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

# --- Enhanced CSS with more glowing effects and agent boxes ---
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
    .glass-card {
        background: rgba(10,10,10,0.6) !important;
        backdrop-filter: blur(15px);
        border-radius: 1.5em;
        padding: 1.8em;
        margin-bottom: 2em;
        box-shadow: 0 0 20px rgba(29,155,240,0.3), inset 0 0 10px rgba(29,155,240,0.1); /* Enhanced glow */
        border: 1px solid rgba(29,155,240,0.4);
        transition: all 0.3s ease, box-shadow 0.5s ease;
    }
    .glass-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 0 40px rgba(29,155,240,0.5), inset 0 0 20px rgba(29,155,240,0.2); /* Stronger glow on hover */
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

    st.markdown('<div style="display:flex;justify-content:center;width:100%;"><div style="max-width:800px;width:100%;margin:0 auto;">', unsafe_allow_html=True)
    
    try:
        lang = "python"

        overall_start = time.time()

        # --- TUA Call ---
        with st.spinner("Running Task Understanding Agent (TUA)..."):
            tua_start = time.time()
            tua_response = requests.post(
                "http://localhost:8000/api/tua",
                json={"user_prompt": cleaned_prompt, "language": lang},
                timeout=60
            )
            tua_time = time.time() - tua_start
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
            std_start = time.time()
            std_response = requests.post(
                "http://localhost:8000/api/std",
                json={"structured_prompt": tua_result.get("structured_prompt", ""), "language": lang},
                timeout=60
            )
            std_time = time.time() - std_start
        if std_response.status_code == 200:
            std_result = std_response.json()
            std_data = std_result.get('std_result', std_result)  # Fix: Handle nested or direct dict
            st.session_state.std_output = std_data
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
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
                st.markdown(f'<div class="subtask-box"><b>Explanation:</b><br>{explanation}</div>', unsafe_allow_html=True)
            subtasks = std_data.get("subtasks", None)
            if subtasks is None:
                # Parse from llm_response if None
                llm_resp = std_data.get("llm_response", "")
                subtasks_match = re.search(r'Subtasks:\s*(.*)', llm_resp, re.DOTALL)
                if subtasks_match:
                    subtasks_text = subtasks_match.group(1).strip().split('\n')
                    subtasks = [{'step': i+1, 'description': s.strip('* ').strip()} for i, s in enumerate(subtasks_text) if s.strip()]
            if subtasks and classification != "SIMPLE":  # Only show subtasks for non-simple
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

        # --- PRA Call ---
        with st.spinner("Running Prompt Refiner Agent (PRA)..."):
            pra_start = time.time()
            pra_input = {
                "tua": st.session_state["tua_output"],
                "std": st.session_state["std_output"]
            }
            pra_response = requests.post("http://localhost:8000/api/pra", json=pra_input, timeout=60)
            pra_time = time.time() - pra_start
            if pra_response.status_code == 200:
                pra_result = pra_response.json()
                st.session_state.pra_output = pra_result
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown("<h4 style='margin-bottom:0.5em;'>Prompt Refiner Agent (PRA) <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
                refined_prompts = pra_result.get("refined_prompts", [])
                if refined_prompts:
                    if len(refined_prompts) == 1 and refined_prompts[0].get('subtask') == 'Complete Solution':
                        st.markdown("<b>Complete Solution Refined:</b>", unsafe_allow_html=True)
                        st.code(refined_prompts[0].get('refined_prompt', ''), language="text")  # Display refined prompt
                    else:
                        for item in refined_prompts:
                            subtask_label = item.get('subtask', 'Main Task')
                            st.markdown(f"<b>{subtask_label}:</b>", unsafe_allow_html=True)
                            st.code(item.get('refined_prompt', ''), language="text")  # Display refined prompt for each subtask
                else:
                    st.warning("No refined prompts generated by PRA.")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.error(f"PRA API failed with status {pra_response.status_code}: {pra_response.text}")
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown("<h4 style='margin-bottom:0.5em;'>Prompt Refiner Agent (PRA) <span class='subtask-status subtask-failed'>Failed</span></h4>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.stop()

        # --- Full Pipeline Execution (Code Agent, Tester, Debugger) ---
        refined_prompt = st.session_state.get("refined_prompt", "")
        original_prompt = st.session_state.get('last_prompt', prompt_text)
        pipeline_prompt = refined_prompt if refined_prompt else original_prompt

        if not pipeline_prompt:
            st.error("No valid prompt available for pipeline execution.")
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>Pipeline Error <span class='subtask-status subtask-failed'>Failed</span></h4>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()

        with st.spinner("Running Code Agent → Tester Agent → SelfDebugger (if needed)..."):
            pipeline_start = time.time()
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
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
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
            code_source = pipeline_result.get("code_source", "unknown")
            st.markdown(f"**Source:** {code_source}", unsafe_allow_html=True)
            if st.button("Export Code", key="export_code"):
                st.download_button("Download Code", code, file_name="solution.py")
            st.markdown('</div>', unsafe_allow_html=True)

            # Tester Agent Card
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
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
                    if "error" in test_results:
                        st.error(f"Overall Error: {test_results['error']}")
                else:
                    st.warning(f"Test Status: {status} ({passed}/{total})")
                detailed_results = test_results.get("detailed_test_results", [])
                if detailed_results:
                    st.markdown("**Test Cases:**")
                    for res in detailed_results:
                        test_class = "test-pass" if res["status"] == "pass" else "test-fail"
                        icon = "✅" if res["status"] == "pass" else "❌"
                        error_text = res.get('error', '').replace('\\', '\\\\') if 'error' in res else ''
                        error_html = f"<br><span style=\"color:#ff0000;\">Error: {error_text}</span>" if 'error' in res else ""
                        st.markdown(f'<div class="test-bubble {test_class}">'
                                    f'<span class="test-icon">{icon}</span>'
                                    f'<code>{res["test"]}</code>'
                                    f'{error_html}'
                                    f'</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # SelfDebugger Card (if debugged)
            if "debug_explanation" in pipeline_result:
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown("<h4 style='margin-bottom:0.5em;'>SelfDebugger Agent <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
                safe_explanation = pipeline_result['debug_explanation'].replace('\\', '\\\\') if 'debug_explanation' in pipeline_result else ""
                st.markdown(f"<b>Explanation:</b> {safe_explanation}", unsafe_allow_html=True)
                with st.expander("Fixed Code"):
                    st.code(pipeline_result["code"], language="python")
                st.markdown('</div>', unsafe_allow_html=True)

            # Timing Summary
            total_time = time.time() - overall_start
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>Timing Summary <span class='subtask-status subtask-complete'>Completed</span></h4>", unsafe_allow_html=True)
            st.markdown(f"- TUA: {tua_time:.2f}s")
            st.markdown(f"- STD: {std_time:.2f}s")
            st.markdown(f"- PRA: {pra_time:.2f}s")
            st.markdown(f"- Pipeline (Code/Test/Debug): {pipeline_time:.2f}s")
            st.markdown(f"- Total Time: {total_time:.2f}s")
            st.markdown('</div>', unsafe_allow_html=True)

        else:
            st.error(f"Pipeline API failed with status {full_pipeline_response.status_code}: {full_pipeline_response.text}")

    except Exception as e:
        st.error(f"Error in execution: {str(e)}")
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("<h4 style='margin-bottom:0.5em;'>Pipeline Error <span class='subtask-status subtask-failed'>Failed</span></h4>", unsafe_allow_html=True)
        st.code(traceback.format_exc(), language="python")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)
