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
        background: #0e1117;
    }
    .stMarkdown {
        font-family: 'Inter', sans-serif;
    }
    div[data-testid="stExpander"] div[role="button"] p {
        font-size: 1.1rem;
        font-weight: 600;
        color: #00ADB5;
    }
    .metric-card {
        background-color: #222831;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #393E46;
        text-align: center;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #EEEEEE;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: bold;
        color: #00ADB5;
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

# --- Main Panel ---
st.title("🤖 Agentic Compliance Payment System")

# Transaction Monitor
cols = st.columns(3)
ledger = st.session_state.current_ledger
def metric_card(col, label, value):
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">${value:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

monitor_container = st.empty()
with monitor_container.container():
     c1, c2, c3 = st.columns(3)
     metric_card(c1, "Buyer Wallet", ledger["buyer_balance"])
     metric_card(c2, "Escrow Vault", ledger["escrow_balance"])
     metric_card(c3, "Seller Wallet", ledger["seller_balance"])


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
log_container = st.container() 

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
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    
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
                     with st.chat_message(name=agent, avatar="🤖"):
                        st.markdown(f"**{agent}**: {thought}")
                        if log_item:
                             st.code(log_item)
                
                # Live Update Monitor
                with monitor_container.container():
                     c1, c2, c3 = st.columns(3)
                     metric_card(c1, "Buyer Wallet", st.session_state.current_ledger["buyer_balance"])
                     metric_card(c2, "Escrow Vault", st.session_state.current_ledger["escrow_balance"])
                     metric_card(c3, "Seller Wallet", st.session_state.current_ledger["seller_balance"])
                
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
