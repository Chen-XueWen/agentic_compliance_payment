from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

from src.state import GraphState
from src.agents.buyer import node_analyze_intent, node_negotiate_acceptance
from src.agents.compliance import (
    node_evaluate_compliance, 
    node_propose_escrow, 
    node_execute_escrow, 
    node_finalize_settlement
)

# --- Routing Logic ---

def route_compliance(state: GraphState):
    status = state["compliance_status"]
    if status == "PENDING":
        return "propose_escrow"
    else:
        return "direct_settle" # Not fully implemented in happy path demo

# --- Graph Construction ---

def build_graph():
    workflow = StateGraph(GraphState)
    
    # Add Nodes
    workflow.add_node("analyze_intent", node_analyze_intent)
    workflow.add_node("evaluate_compliance", node_evaluate_compliance)
    workflow.add_node("propose_escrow", node_propose_escrow)
    workflow.add_node("negotiate_acceptance", node_negotiate_acceptance)
    workflow.add_node("execute_escrow", node_execute_escrow)
    workflow.add_node("finalize_settlement", node_finalize_settlement)
    
    # Set Entry Point
    workflow.set_entry_point("analyze_intent")
    
    # Add Edges
    workflow.add_edge("analyze_intent", "evaluate_compliance")
    
    workflow.add_conditional_edges(
        "evaluate_compliance",
        route_compliance,
        {
            "propose_escrow": "propose_escrow",
            "direct_settle": END # Short circuit for low value
        }
    )
    
    workflow.add_edge("propose_escrow", "negotiate_acceptance")
    workflow.add_edge("negotiate_acceptance", "execute_escrow")
    
    # Interrupt after execute_escrow, then resume to finalize_settlement
    workflow.add_edge("execute_escrow", "finalize_settlement") 
    workflow.add_edge("finalize_settlement", END)
    
    return workflow

# Create the graph instance with memory
memory = MemorySaver()
app_graph = build_graph().compile(checkpointer=memory, interrupt_after=["propose_escrow", "execute_escrow"])
