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

# Custom dark theme CSS
st.markdown(
    """
    <style>
    body, .stApp { background-color: #18181b !important; color: #f3f4f6 !important; }
    .stTextInput>div>div>input, .stSelectbox>div>div>div>input { background: #27272a !important; color: #f3f4f6 !important; }
    .stButton>button { background: #27272a !important; color: #f3f4f6 !important; border-radius: 8px; border: 1px solid #52525b; }
    .stMarkdown, .stCodeBlock, .stTextArea>div>textarea { background: #18181b !important; color: #f3f4f6 !important; }
    .st-bb, .st-cq, .st-cv, .st-cw, .st-cx, .st-cy, .st-cz { background: #18181b !important; }
    .st-cp { color: #a3e635 !important; }
    .st-cq { color: #38bdf8 !important; }
    .st-cr { color: #f472b6 !important; }
    .st-cs { color: #facc15 !important; }
    .st-ct { color: #f87171 !important; }
    .st-cu { color: #34d399 !important; }
    .st-cv { color: #f3f4f6 !important; }
    .st-cw { color: #f3f4f6 !important; }
    .st-cx { color: #f3f4f6 !important; }
    .st-cy { color: #f3f4f6 !important; }
    .st-cz { color: #f3f4f6 !important; }
    .st-c0 { color: #f3f4f6 !important; }
    .st-c1 { color: #f3f4f6 !important; }
    .st-c2 { color: #f3f4f6 !important; }
    .st-c3 { color: #f3f4f6 !important; }
    .st-c4 { color: #f3f4f6 !important; }
    .st-c5 { color: #f3f4f6 !important; }
    .st-c6 { color: #f3f4f6 !important; }
    .st-c7 { color: #f3f4f6 !important; }
    .st-c8 { color: #f3f4f6 !important; }
    .st-c9 { color: #f3f4f6 !important; }
    .st-ca { color: #f3f4f6 !important; }
    .st-cb { color: #f3f4f6 !important; }
    .st-cc { color: #f3f4f6 !important; }
    .st-cd { color: #f3f4f6 !important; }
    .st-ce { color: #f3f4f6 !important; }
    .st-cf { color: #f3f4f6 !important; }
    .st-cg { color: #f3f4f6 !important; }
    .st-ch { color: #f3f4f6 !important; }
    .st-ci { color: #f3f4f6 !important; }
    .st-cj { color: #f3f4f6 !important; }
    .st-ck { color: #f3f4f6 !important; }
    .st-cl { color: #f3f4f6 !important; }
    .st-cm { color: #f3f4f6 !important; }
    .st-cn { color: #f3f4f6 !important; }
    .st-co { color: #f3f4f6 !important; }
    .st-cp { color: #f3f4f6 !important; }
    .st-cq { color: #f3f4f6 !important; }
    .st-cr { color: #f3f4f6 !important; }
    .st-cs { color: #f3f4f6 !important; }
    .st-ct { color: #f3f4f6 !important; }
    .st-cu { color: #f3f4f6 !important; }
    .st-cv { color: #f3f4f6 !important; }
    .st-cw { color: #f3f4f6 !important; }
    .st-cx { color: #f3f4f6 !important; }
    .st-cy { color: #f3f4f6 !important; }
    .st-cz { color: #f3f4f6 !important; }
    .st-c0 { color: #f3f4f6 !important; }
    .st-c1 { color: #f3f4f6 !important; }
    .st-c2 { color: #f3f4f6 !important; }
    .st-c3 { color: #f3f4f6 !important; }
    .st-c4 { color: #f3f4f6 !important; }
    .st-c5 { color: #f3f4f6 !important; }
    .st-c6 { color: #f3f4f6 !important; }
    .st-c7 { color: #f3f4f6 !important; }
    .st-c8 { color: #f3f4f6 !important; }
    .st-c9 { color: #f3f4f6 !important; }
    .st-ca { color: #f3f4f6 !important; }
    .st-cb { color: #f3f4f6 !important; }
    .st-cc { color: #f3f4f6 !important; }
    .st-cd { color: #f3f4f6 !important; }
    .st-ce { color: #f3f4f6 !important; }
    .st-cf { color: #f3f4f6 !important; }
    .st-cg { color: #f3f4f6 !important; }
    .st-ch { color: #f3f4f6 !important; }
    .st-ci { color: #f3f4f6 !important; }
    .st-cj { color: #f3f4f6 !important; }
    .st-ck { color: #f3f4f6 !important; }
    .st-cl { color: #f3f4f6 !important; }
    .st-cm { color: #f3f4f6 !important; }
    .st-cn { color: #f3f4f6 !important; }
    .st-co { color: #f3f4f6 !important; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("spar.ai")
st.markdown("""
type your DSA problem and select a language. the assistant will parse constraints, generate a structured prompt, and show backend steps.
""")

# Sidebar for language selection
with st.sidebar:
    st.header("Settings")
    language = st.selectbox("programming language", ["python", "java", "c++", "JavaScript", "go", "rust"])
    if language is None:
        language = "python"  # Fallback to Python if somehow None

# Main input area
problem_text = st.text_area("enter your DSA problem:", height=120, key="problem_input")

if st.button("Submit", use_container_width=True):
    if not problem_text.strip():
        st.warning("please enter a problem statement.")
    else:
        try:
            # Ensure language is always a string
            lang = language if language is not None else "python"
            # Step 1: Process user input
            st.markdown("**Step 1: Processing user input...**")
            user_input = input_handler.get_user_input(problem_text, lang)
            st.json(user_input)
            # Step 2: Task Understanding Agent
            st.markdown("**Step 2: TaskUnderstandingAgent generating structured prompt...**")
            structured = task_understanding_node(user_input)
            st.json(structured)
            st.markdown("---")
            st.markdown("### Final Structured Prompt")
            st.code(structured.get("structured_prompt", "[No prompt generated]"), language="markdown")
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.code(traceback.format_exc(), language="python")

# Show task history (robust to missing attribute)
task_history = getattr(input_handler, "task_history", [])
if task_history:
    st.markdown("---")
    st.markdown("#### Task History")
    for entry in reversed(task_history[-5:]):
        st.markdown(f"- `{entry.get('timestamp', '')}` | **{entry.get('original_prompt', '')}** | {entry.get('language', '')} | Constraints: `{entry.get('constraints', '')}`")







