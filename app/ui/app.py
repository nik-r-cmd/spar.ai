import sys
import os
# Dynamically add the project root to sys.path if not already present
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
from app.modules import input_handler
from app.graph.nodes import task_understanding_node
import traceback
import asyncio
import json
from app.modules.orchestrator import orchestrate_dag

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

# Sidebar: language selector and task history
with st.sidebar:
    st.markdown('<div class="sidebar-title">settings</div>', unsafe_allow_html=True)
    language = st.selectbox("programming language", ["python", "java", "c++", "JavaScript", "go", "rust"])
    llm_mode = st.selectbox("LLM mode", ["auto", "llm_only", "heuristic_only", "mock"], index=0)
    from app.modules.input_handler import LLMMode
    input_handler.LLM_MODE = LLMMode(llm_mode)
    st.markdown('<div class="sidebar-title">task history</div>', unsafe_allow_html=True)
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

# --- Custom CSS for enterprise chat look ---
st.markdown(
    """
    <style>
    body, .stApp {
        background: #18181b !important;
        color: #f3f4f6 !important;
    }
    .main-title {
        text-align: center;
        font-size: 2.7em;
        font-weight: 900;
        letter-spacing: -2px;
        background: linear-gradient(90deg,#5a6ee5,#7f8fa6 80%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.7em;
        margin-top: 0.7em;
        font-family: 'Poppins', 'Inter', 'Segoe UI', Arial, sans-serif;
        text-shadow: 0 2px 16px rgba(90,110,229,0.10);
    }
    .prompt-row {
        display: flex;
        align-items: center;
        justify-content: center;
        margin-top: 2.5em;
        margin-bottom: 1.5em;
        width: 100%;
    }
    .prompt-textarea {
        flex: 1;
        min-height: 64px;
        max-height: 180px;
        background: #232336;
        color: #f3f4f6;
        border-radius: 2em;
        font-size: 1.1em;
        font-family: 'Poppins', 'Inter', 'Segoe UI', Arial, sans-serif;
        border: 1.5px solid #2d3559;
        padding: 1.2em 1.5em;
        margin-right: 0.7em;
        box-shadow: 0 2px 12px 0 rgba(90,110,229,0.10);
        outline: none;
        resize: none;
        transition: border 0.2s;
    }
    .prompt-textarea:focus {
        border: 1.5px solid #5a6ee5;
    }
    .send-btn {
        background: linear-gradient(90deg,#5a6ee5,#7f8fa6 80%);
        color: #fff;
        border-radius: 50%;
        width: 56px;
        height: 56px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.7em;
        border: none;
        box-shadow: 0 2px 12px 0 rgba(90,110,229,0.10);
        cursor: pointer;
        transition: box-shadow 0.2s, background 0.2s;
        outline: none !important;
    }
    .send-btn:focus, .send-btn:active {
        outline: none !important;
        border: none !important;
        box-shadow: 0 4px 24px 0 rgba(90,110,229,0.18);
    }
    .send-btn:hover {
        background: linear-gradient(90deg,#7f8fa6,#5a6ee5 80%);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Main area title ---
st.markdown('<div class="main-title">spar<span style="font-weight:400;">.ai</span></div>', unsafe_allow_html=True)

# --- Prompt input row: glassmorphism, centered, Cursor-style ---
st.markdown(
    """
    <style>
    .centered-input-container {
        display: flex;
        flex-direction: row;
        align-items: flex-end;
        justify-content: center;
        margin-top: 1.2em;
        margin-bottom: 1.5em;
        width: 100%;
    }
    .input-inner {
        display: flex;
        flex-direction: row;
        align-items: flex-end;
        background: rgba(40, 42, 55, 0.55);
        border-radius: 2em;
        box-shadow: 0 4px 32px 0 rgba(90,110,229,0.10), 0 1.5px 16px 0 rgba(255,255,255,0.08) inset;
        backdrop-filter: blur(8px);
        max-width: 650px;
        width: 100%;
        padding: 0.2em 0.4em 0.2em 1.2em;
        margin: 0 auto;
    }
    .glass-textarea textarea {
        background: transparent !important;
        color: #f3f4f6 !important;
        border-radius: 2em !important;
        font-size: 1.15em !important;
        font-family: 'Poppins', 'Inter', 'Segoe UI', Arial, sans-serif !important;
        border: none !important;
        box-shadow: none !important;
        outline: none;
        min-height: 56px;
        max-height: 180px;
        resize: none;
        padding: 1.1em 0.5em 1.1em 0.1em !important;
        margin-bottom: 0;
        width: 100%;
    }
    .glass-textarea textarea::placeholder {
        color: #b3b8d0 !important;
        font-size: 1.08em !important;
        opacity: 1 !important;
    }
    .glass-send-btn {
        background: linear-gradient(90deg,#5a6ee5,#7f8fa6 80%);
        color: #fff;
        border-radius: 50%;
        width: 48px;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.7em;
        border: none;
        box-shadow: 0 2px 12px 0 rgba(90,110,229,0.10);
        cursor: pointer;
        margin-left: 0.7em;
        margin-bottom: 0.2em;
        transition: box-shadow 0.2s, background 0.2s;
        outline: none !important;
    }
    .glass-send-btn:focus, .glass-send-btn:active {
        outline: none !important;
        border: none !important;
        box-shadow: 0 4px 24px 0 rgba(90,110,229,0.18);
    }
    .glass-send-btn:hover {
        background: linear-gradient(90deg,#7f8fa6,#5a6ee5 80%);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Centered input row with max width, Cursor-style, always under logo ---
st.markdown('<div class="centered-input-container"><div class="input-inner">', unsafe_allow_html=True)
col1, col2 = st.columns([8,1], gap="small")
with col1:
    prompt_text = st.text_area(
        "",
        placeholder="enter your DSA problem...",
        key="prompt_input",
        height=64,
        label_visibility="collapsed"
    )
with col2:
    send_clicked = st.button(
        label="↑",  # Upward arrow for send, like Cursor UI
        key="send_btn",
        use_container_width=True,
        help="Send"
    )
st.markdown('</div></div>', unsafe_allow_html=True)

# --- Centered output container below input row, same max width ---
if send_clicked and prompt_text.strip():
    st.markdown('<div style="display:flex;justify-content:center;width:100%;"><div style="max-width:650px;width:100%;margin:0 auto;">', unsafe_allow_html=True)
    problem_text = prompt_text
    try:
        lang = language if language is not None else "python"
        st.markdown("**Step 1: Processing user input...**")
        user_input = input_handler.get_user_input(problem_text, lang)
        st.json(user_input)
        corrected_prompt = user_input.get("corrected_prompt", "")
        if corrected_prompt:
            st.markdown("**Corrected Prompt:**")
            st.code(corrected_prompt, language="text")
        if user_input.get("ambiguity_flags"):
            st.warning(f"Ambiguity flags: {', '.join(user_input['ambiguity_flags'])}")
        st.markdown("**Step 2: TaskUnderstandingAgent generating structured prompt...**")
        structured = task_understanding_node(user_input)
        st.json(structured)
        from app.modules.input_handler import SubtaskDistributor
        st.markdown("---")
        st.markdown("### SubtaskDistributor: Task Routing & Decomposition")
        st.markdown("This module decides if your problem is atomic (simple) or needs to be split into subtasks (complex). See below how your problem is routed:")
        distributor = SubtaskDistributor()
        subtask_output, fallback_used = distributor.distribute_task(structured)
        dag_dict = subtask_output.to_dict()
        if fallback_used:
            st.warning("LLM unavailable or LLM mode set to heuristic/mock. Heuristic fallback was used for task classification/decomposition.")
        if len(dag_dict) == 1:
            st.success("**Task classified as SIMPLE.**\n\nIt will be sent directly to the next agent.")
            for sub in dag_dict.values():
                st.json(sub)
        else:
            st.info("**Task classified as COMPLEX.**\n\nIt will be split into the following subtasks (DAG):")
            for sub in dag_dict.values():
                st.markdown(f"**{sub['name']}** (depends on: {', '.join(sub['depends_on']) if sub['depends_on'] else 'None'})")
                st.code(sub['prompt'], language="text")
        st.markdown("---")
        st.markdown("### Orchestration: Subtask Execution & Progress")
        progress_placeholder = st.empty()
        results_placeholder = st.empty()
        export_placeholder = st.empty()
        async def simple_executor(subtask):
            import random
            import asyncio
            await asyncio.sleep(random.uniform(0.5, 1.5))
            subtask.result = f"Result for {subtask.name}"
        def run_orchestration():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            dag = subtask_output
            progress = {name: sub.status for name, sub in dag.subtasks.items()}
            def update_ui(dag):
                progress = {name: sub.status for name, sub in dag.subtasks.items()}
                progress_placeholder.write(f"**Progress:** {json.dumps(progress)}")
                results = {name: sub.result for name, sub in dag.subtasks.items() if sub.result}
                if results:
                    results_placeholder.write("**Intermediate Results:**")
                    results_placeholder.json(results)
            final_dag = loop.run_until_complete(
                orchestrate_dag(dag, simple_executor, update_callback=update_ui)
            )
            loop.close()
            return final_dag
        if st.button("Run Subtasks", use_container_width=True):
            final_dag = run_orchestration()
            st.success("All subtasks executed. See results below.")
            st.json(final_dag.to_dict())
            export_placeholder.download_button(
                label="Export Results as JSON",
                data=json.dumps(final_dag.to_dict(), indent=2),
                file_name="subtask_results.json",
                mime="application/json"
            )
    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.code(traceback.format_exc(), language="python")
    st.markdown('</div></div>', unsafe_allow_html=True)

# --- Custom CSS for modern dark mode, gradients, 3D cards, and beautiful sidebar ---
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
    </style>
    """,
    unsafe_allow_html=True
)







