import streamlit as st
import base64
from langchain_core.messages import HumanMessage
from typing import Dict
import time
import streamlit.components.v1 as components

# Import our backend
from agent_graph import app_graph, GraphState

# --- Config ---
st.set_page_config(page_title="Agentic Compliance Payment", layout="wide")

# --- Styles ---
st.markdown("""
<style>
    .reportview-container {
        background: #ffffff;
    }
    .stMarkdown {
        font-family: 'Inter', sans-serif;
    }
    div[data-testid="stExpander"] div[role="button"] p {
        font-size: 1.1rem;
        font-weight: 600;
        color: #00ADB5;
    }
    
    /* Wallet Sticky Container - Light Glassmorphism */
    .wallet-sticky-container {
        position: sticky;
        top: 0;
        z-index: 9999;
        background: rgba(255, 255, 255, 0.95); /* White background */
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 10px 0 20px 0;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    
    .wallet-grid {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    /* Metric Card - Light Theme */
    .metric-card {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        flex: 1;
        min-width: 0;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .metric-card:hover {
        border-color: #00ADB5;
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #555555; /* Dark gray text */
        margin-bottom: 5px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #333333; /* Darker text for value */
        text-shadow: none;
    }
</style>
""", unsafe_allow_html=True)

# --- State Init ---
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"session_{int(time.time())}"
if "graph_started" not in st.session_state:
    st.session_state.graph_started = False
if "messages_log" not in st.session_state:
    st.session_state.messages_log = []
if "current_ledger" not in st.session_state:
    st.session_state.current_ledger = {"buyer_balance": 10000, "seller_balance": 0, "escrow_balance": 0}
if "compliance_status" not in st.session_state:
    st.session_state.compliance_status = "IDLE"

def render_mermaid(code: str, height=500):
    """Renders Mermaid.js diagram using HTML component"""
    html_code = f"""
    <div class="mermaid">
    {code}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'dark', securityLevel: 'loose' }});
    </script>
    """
    return components.html(html_code, height=height)

def get_graph_mermaid(active_node=None):
    """Generates the Mermaid Graph syntax with highlighting"""
    try:
        # Get base mermaid
        base_mmd = app_graph.get_graph().draw_mermaid()
        
        # Add styling for active node
        if active_node:
            # High contrast style: Yellow fill, Red border, Black text
            style = f"\nstyle {active_node} fill:#F4D03F,stroke:#E74C3C,stroke-width:4px,color:#000000"
            return base_mmd + style
        return base_mmd
    except Exception as e:
        st.error(f"Could not generate mermaid: {e}")
        return None

# --- Sidebar ---
with st.sidebar:
    st.title("Workflow State")
    
    # Real-time Graph Visualizer
    graph_container = st.empty()
    
    # Initial Render
    with graph_container.container():
         # We need to determine the active node from the state effectively to highlight it initially or during updates
         # For initial state, it's usually empty or 'start'
         mmd = get_graph_mermaid()
         if mmd:
             render_mermaid(mmd, height=600)

    st.markdown("---")
    st.subheader("System Status")
    status_color = "🟢" if st.session_state.compliance_status == "PASS" else "🟡" if st.session_state.compliance_status in ["PENDING", "ESCROW_ACTIVE"] else "⚪"
    st.markdown(f"**Compliance Status:** {status_color} `{st.session_state.compliance_status}`")

from langchain_core.callbacks import BaseCallbackHandler

class StreamlitTokenStreamer(BaseCallbackHandler):
    def __init__(self, container):
        self.container = container
        self.placeholder = None
        self.text = ""
        self.stream_box = None
        
    def on_llm_start(self, serialized, prompts, **kwargs):
        self.text = ""
        # Determine agent from tags if available
        tags = kwargs.get("tags", [])
        agent_name = tags[0] if tags else "Agent"
        
        # Create a chat message placeholder for streaming
        self.stream_box = self.container.chat_message(name=agent_name, avatar="🤖")
        self.placeholder = self.stream_box.empty()
        self.placeholder.markdown("...")
        
    def on_llm_new_token(self, token, **kwargs):
        self.text += token
        self.placeholder.markdown(self.text + "▌")
        
    def on_llm_end(self, response, **kwargs):
        # Finalize the message without the cursor
        self.placeholder.markdown(self.text)

# --- Main Panel ---
st.title("🤖 Agentic Compliance Payment System")

# Transaction Monitor (Sticky Wallet)
ledger = st.session_state.current_ledger

def render_wallet_html(current_ledger):
    return f"""
    <div class="wallet-sticky-container">
        <div class="wallet-grid">
            <div class="metric-card">
                <div class="metric-label">Buyer Wallet</div>
                <div class="metric-value">${current_ledger['buyer_balance']:,.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Escrow Vault</div>
                <div class="metric-value">${current_ledger['escrow_balance']:,.2f}</div>
            </div>
             <div class="metric-card">
                <div class="metric-label">Seller Wallet</div>
                <div class="metric-value">${current_ledger['seller_balance']:,.2f}</div>
            </div>
        </div>
    </div>
    """

monitor_container = st.empty()
monitor_container.markdown(render_wallet_html(ledger), unsafe_allow_html=True)


st.divider()

# Input Section
input_col, controls_col = st.columns([2, 1])

with input_col:
    buyer_request = st.text_input("Buyer Request", value="I want a $1500 luxury watch")

with controls_col:
    st.write("") # Spacer
    st.write("") 
    start_btn = st.button("Start Transaction", type="primary", disabled=st.session_state.graph_started)

# "Thinking" Log
st.subheader("Agent Internals & Negotiation Log")
log_container = st.container(height=500) 

# Render History
def render_history_to_container(container):
    with container:
        for msg in st.session_state.messages_log:
            with st.chat_message(name=msg["agent"], avatar="🤖"):
                st.markdown(f"**{msg['agent']}**: {msg['thought']}")
                if msg.get("log"):
                    st.code(msg["log"])

# Helper for look-ahead prediction
def get_next_node(current_node, status):
    if current_node == "analyze_intent":
        return "evaluate_compliance"
    elif current_node == "evaluate_compliance":
        return "propose_escrow" if status == "PENDING" else "direct_settle"
    elif current_node == "propose_escrow":
        return "negotiate_acceptance"
    elif current_node == "negotiate_acceptance":
        return "execute_escrow"
    elif current_node == "execute_escrow":
        return "finalize_settlement"
    return current_node

# Always render existing history
render_history_to_container(log_container)

# Helper to run the graph
def run_interaction(inputs=None, resume=False):
    # Setup Custom Token Streamer for Main Log
    st_callback = StreamlitTokenStreamer(container=log_container)
    
    # Pass callbacks to the graph config
    config = {
        "configurable": {"thread_id": st.session_state.thread_id},
        "callbacks": [st_callback]
    }
    
    # Use the shared container
    container_expander = log_container
    
    try:
        iterator = app_graph.stream(inputs, config=config) if not resume else app_graph.stream(None, config=config)
        
        for event in iterator:
            for node_name, state_update in event.items():
                # Skip non-dict updates (like interrupts)
                if not isinstance(state_update, dict):
                    continue
                    
                # Update Session State
                st.session_state.current_ledger = state_update.get("ledger", st.session_state.current_ledger)
                st.session_state.compliance_status = state_update.get("compliance_status", st.session_state.compliance_status)
                
                thought = state_update.get("current_thought", "")
                agent = state_update.get("active_agent", "SYSTEM")
                neg_log = state_update.get("negotiation_log", [])
                log_item = neg_log[-1] if neg_log else None
                
                # Append to History
                st.session_state.messages_log.append({
                    "agent": agent,
                    "thought": thought,
                    "log": log_item
                })

                # Render Update (Stream new item)
                with container_expander:
                     # Thought already streamed by callback, so we don't render it here.
                     # Only render the formal log if present.
                     if log_item:
                         # We put it in a separate code block for now, or we could try to append to the previous chat message
                         # but accessing the previous container is hard.
                         # Rendering it as a standalone code block is clear enough.
                         st.code(log_item)
                
                # Live Update Monitor
                monitor_container.markdown(render_wallet_html(st.session_state.current_ledger), unsafe_allow_html=True)
                
                # LOOK-AHEAD: Predict next node to highlight NOW (while backend is crunching)
                next_node = get_next_node(node_name, st.session_state.compliance_status)
                
                # Update Graph with Next Node
                with graph_container.container():
                     mmd = get_graph_mermaid(active_node=next_node)
                     if mmd:
                         render_mermaid(mmd, height=500)
                     st.caption(f"Active: `{next_node}`") 
                
                # Removed artificial sleep to reduce lag
                # time.sleep(0.8) 
                
    except Exception as e:
        st.error(f"Interaction Error: {e}")


# Interaction Logic
if start_btn:
    st.session_state.graph_started = True
    st.session_state.messages_log = [] # Clear old logs
    st.session_state.compliance_status = "STARTING" # Immediate feedback
    st.rerun()

if st.session_state.compliance_status == "STARTING":
    # Pre-render graph to show activity immediately
    with graph_container.container():
         mmd = get_graph_mermaid(active_node="analyze_intent") # Guess first node
         if mmd:
             render_mermaid(mmd, height=500)
         st.caption("Active: `analyze_intent`")
    
    initial_inputs = {
        "messages": [HumanMessage(content=buyer_request)],
        "ledger": {"buyer_balance": 10000, "seller_balance": 0, "escrow_balance": 0},
        # Reset other keys if needed
        "buyer_intent": {},
        "negotiation_log": []
    }
    
    run_interaction(initial_inputs)

# Source of Funds Upload
if st.session_state.compliance_status == "ESCROW_ACTIVE":
    st.warning("⚠️ Transaction Paused. Source of Funds Proof Required.")
    
    uploaded_file = st.file_uploader("Upload 'mock_sof.txt'", type=["txt"])
    
    if uploaded_file is not None:
        if st.button("Submit Proof"):
            # Mock verification
            content = uploaded_file.read().decode("utf-8")
            if "Balance: $50,000" in content:
                st.success("Document Analyzed. Balance Verified.")
                
                # Update State to reflect SoF AND preserve Ledger/Status
                # Warning: updating 'as_node' might overwrite other keys output by that node if not included.
                # We simply want to modify the buyer_intent (add SoF) but keep the ledger calculation that happened.
                st.session_state.current_ledger["active_agent"] = "LEDGER" # Ensure consistency
                
                config = {"configurable": {"thread_id": st.session_state.thread_id}}
                app_graph.update_state(
                    config, 
                    {
                        "buyer_intent": {"amount": 1500, "attached_vcs": {"sanctions": True, "sof": True}},
                        "ledger": st.session_state.current_ledger,
                        "compliance_status": "ESCROW_ACTIVE",
                        "active_agent": "LEDGER",
                        "negotiation_log": ["Chain: Tx confirmed. Funds Locked. (SoF Verified)"]
                    }, 
                    as_node="execute_escrow" 
                )
                
                # Resume
                run_interaction(resume=True)
            else:
                st.error("Invalid Document. Funds not verified.")

if st.session_state.compliance_status == "PASS":
    st.balloons()
    st.success("✅ Transaction Settled Successfully!")
    # Reset state to enable button again
    st.session_state.graph_started = False
