import sys
import os
# Dynamically add the project root to sys.path if not already present
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

# Remove settings (mode/language) and default to Python only
# Remove sidebar language/mode selectors and history
# Update sidebar color to match screenshot (dark, no blue accent)
# Update font to match screenshot (bold, modern, e.g., 'Inter', 'Poppins', or 'Segoe UI')
# Remove suggestion cards
# Update main area title and subtitle to match screenshot
# Update flow/progress bar to only go up to PromptRefiner
# Implement stage highlighting (active stage: accent color, others: muted)
# Refactor logic: display TUA result as soon as available, then show 'Executing STD...' and update with STD result
# Subtasks: display as glassmorphic bubbles with status badge (pending/complete) next to each

# Move custom CSS injection to the very top to prevent flicker
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
    /* Professional, subtle boxes for explanation and subtasks */
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

# --- Visual Pipeline/Progress Bar ---
st.markdown(
    '''
    <div style="display:flex;justify-content:center;align-items:center;margin-bottom:1.5em;">
        <div style="display:flex;align-items:center;gap:0.7em;font-size:1.1em;">
            <span style="padding:0.3em 0.9em;border-radius:16px;background:#232336;color:#a5b4fc;font-weight:600;">User Input</span>
            <span style="font-size:1.5em;color:#a5b4fc;">→</span>
            <span style="padding:0.3em 0.9em;border-radius:16px;background:#232336;color:#a5b4fc;font-weight:600;">TUA</span>
            <span style="font-size:1.5em;color:#a5b4fc;">→</span>
            <span style="padding:0.3em 0.9em;border-radius:16px;background:#232336;color:#a5b4fc;font-weight:600;">PromptRefiner</span>
            <span style="font-size:1.5em;color:#a5b4fc;">→</span>
            <span style="padding:0.3em 0.9em;border-radius:16px;background:#232336;color:#a5b4fc;font-weight:600;">CodeAgent</span>
        </div>
    </div>
    ''', unsafe_allow_html=True)

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

# # --- Glassmorphic pipeline bar ---
# st.markdown('''
# <div style="display:flex;justify-content:center;margin-bottom:2.5em;">
#   <div style="background:rgba(36,37,46,0.7);backdrop-filter:blur(8px);border-radius:2em;padding:0.7em 1.2em;display:flex;gap:0.7em;box-shadow:0 4px 32px 0 rgba(165,180,252,0.10);">
#     <span style="background:linear-gradient(90deg,#232336,#35354a);color:#b3b3c6;font-weight:700;padding:0.5em 1.3em;border-radius:1.5em;font-size:1.1em;box-shadow:0 2px 8px 0 rgba(165,180,252,0.07);">User Input</span>
#     <span style="color:#b3b3c6;font-size:1.5em;align-self:center;">→</span>
#     <span style="background:linear-gradient(90deg,#232336,#35354a);color:#b3b3c6;font-weight:700;padding:0.5em 1.3em;border-radius:1.5em;font-size:1.1em;box-shadow:0 2px 8px 0 rgba(165,180,252,0.07);">TUA</span>
#     <span style="color:#b3b3c6;font-size:1.5em;align-self:center;">→</span>
#     <span style="background:linear-gradient(90deg,#232336,#35354a);color:#b3b3c6;font-weight:700;padding:0.5em 1.3em;border-radius:1.5em;font-size:1.1em;box-shadow:0 2px 8px 0 rgba(165,180,252,0.07);">Subtask Routing</span>
#     <span style="color:#b3b3c6;font-size:1.5em;align-self:center;">→</span>
#     <span style="background:linear-gradient(90deg,#232336,#35354a);color:#b3b3c6;font-weight:700;padding:0.5em 1.3em;border-radius:1.5em;font-size:1.1em;box-shadow:0 2px 8px 0 rgba(165,180,252,0.07);">PromptRefiner</span>
#   </div>
# </div>
# ''', unsafe_allow_html=True)

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
        # Step 1: Call TUA
        with st.spinner("Running TaskUnderstandingAgent (TUA)..."):
            tua_response = requests.post(
                "http://localhost:8000/api/tua",
                json={"user_prompt": problem_text, "language": lang},
                timeout=60
            )
        if tua_response.status_code == 200:
            tua_result = tua_response.json()
            method_used = tua_result.get('method_used', '')
            print(f"[DEBUG] TUA method_used (from /api/tua): {method_used}")
            # Display TUA result immediately
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom:0.5em;'>TaskUnderstandingAgent (TUA)</h4>", unsafe_allow_html=True)
            with st.expander("Structured Prompt"):
                st.code(tua_result.get("structured_prompt", ""), language="text")
            if method_used:
                st.markdown(f"<b>Method Used:</b> {method_used}", unsafe_allow_html=True)
            constraints = tua_result.get('constraints', '')
            if constraints:
                st.markdown(f"<b>Constraints:</b> {constraints}", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            # Step 2: Call STD with structured prompt
            with st.spinner("Running SubtaskDistributor (STD)..."):
                std_response = requests.post(
                    "http://localhost:8000/api/std",
                    json={"structured_prompt": tua_result.get("structured_prompt", ""), "language": lang},
                    timeout=60
                )
            if std_response.status_code == 200:
                std_result = std_response.json()
                st.markdown('<div class="glass-card">', unsafe_allow_html=True)
                st.markdown("<h4 style='margin-bottom:0.5em;'>SubtaskDistributor (STD)</h4>", unsafe_allow_html=True)
                std_data = std_result.get('std_result', {})
                # Classification badge
                classification = std_data.get("classification", "UNKNOWN")
                if classification == "SIMPLE":
                    st.success(f"**Classification: {classification}**")
                elif classification == "MEDIUM":
                    st.warning(f"**Classification: {classification}**")
                elif classification == "COMPLEX":
                    st.error(f"**Classification: {classification}**")
                else:
                    st.info(f"**Classification: {classification}**")
                # Explanation in glass card
                explanation = std_data.get("explanation", "")
                if explanation:
                    st.markdown('<div class="glass-card" style="margin-bottom:1em;"><b>Explanation:</b><br>' + explanation + '</div>', unsafe_allow_html=True)
                # Subtasks in glass cards
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
        else:
            st.error("TUA backend error")
    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.info("If this persists, please contact support or check the backend logs.")
        st.code(traceback.format_exc(), language="python")
    st.markdown('</div></div>', unsafe_allow_html=True)

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

# NOTE: For true incremental display, backend must provide separate endpoints for TUA and STD. With current backend, only full response can be shown.

























