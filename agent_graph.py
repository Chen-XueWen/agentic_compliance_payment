import json
from typing import TypedDict, Annotated, List, Literal
import operator

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# --- Configuration ---
LLM_MODEL = "gpt-oss:120b"
LLM_BASE_URL = "http://localhost:11434"

# Initialize LLM
llm = ChatOllama(model=LLM_MODEL, base_url=LLM_BASE_URL, temperature=0)

# --- State Definition ---

class GraphState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    buyer_intent: dict      # {item, amount, attached_vcs: {sanctions: bool, sof: bool}}
    seller_offer: dict      # {sku, price, jurisdiction}
    compliance_status: str  # "PASS", "FAIL", "PENDING", "ESCROW_ACTIVE"
    active_agent: str       # "BA", "SA", or "CA"
    negotiation_log: List[str]   # List of structured proposals/logs
    ledger: dict            # {buyer_balance, seller_balance, escrow_balance}
    current_thought: str    # The "internal monologue" of the active agent

# --- Mock Infrastructure ---

def mock_x402_handshake(amount: float, wallet: str):
    """Simulates an x402 protocol handshake."""
    return {
        "x402_header": "allow",
        "signature": f"mock_sig_{int(amount)}_{wallet}",
        "escrow_contract": "0xABC123..."
    }

def mock_ledger_transfer(ledger: dict, source: str, destination: str, amount: float):
    """Updates the simulated ledger."""
    new_ledger = ledger.copy()
    if new_ledger[f"{source}_balance"] >= amount:
        new_ledger[f"{source}_balance"] -= amount
        new_ledger[f"{destination}_balance"] += amount
    return new_ledger

# --- Nodes ---

def node_analyze_intent(state: GraphState):
    """Buyer Agent: Parses user input into structured intent."""
    print("--- BUYER AGENT: ANALYZING INTENT ---")
    messages = state["messages"]
    last_message = messages[-1].content
    
    # LLM Call for Extraction
    prompt = ChatPromptTemplate.from_template(
        "Extract the item and amount from this request: '{request}'. "
        "Return JSON with keys 'item' (string) and 'amount' (float). "
        "If unsure, default to item='Luxury Watch' and amount=1500."
    )
    chain = prompt | llm | StrOutputParser()
    try:
        response = chain.invoke({"request": last_message})
        # Basic cleanup to find JSON
        json_str = response[response.find("{"):response.rfind("}")+1]
        data = json.loads(json_str)
        item = data.get("item", "Luxury Watch")
        amount = float(data.get("amount", 1500))
    except Exception as e:
        print(f"LLM Extraction Failed: {e}")
        item = "Luxury Watch"
        amount = 1500

    buyer_intent = {
        "item": item,
        "amount": amount,
        "attached_vcs": {"sanctions": True, "sof": False}
    }
    
    # LLM Call for Thought
    thought_prompt = ChatPromptTemplate.from_template(
        "You are a Buyer Agent. You processed a request for '{item}' at ${amount}. "
        "You have a Sanctions VC but NO Source of Funds VC. "
        "Think aloud about your current status and what you are submitting."
    )
    thought_chain = thought_prompt | llm | StrOutputParser()
    thought = thought_chain.invoke({"item": item, "amount": amount})
    
    return {
        "buyer_intent": buyer_intent,
        "active_agent": "BA",
        "current_thought": thought,
        "negotiation_log": [f"BA: Initiating purchase for {item} (${amount})."]
    }

def node_evaluate_compliance(state: GraphState):
    """Compliance Agent: Checks Sanctions and Amount."""
    print("--- COMPLIANCE AGENT: EVALUATING ---")
    intent = state["buyer_intent"]
    amount = intent["amount"]
    vcs = intent["attached_vcs"]
    
    # LLM Evaluation
    prompt = ChatPromptTemplate.from_template(
        "You are a Compliance Agent. Rules: \n"
        "1. If amount > 1000 and Source of Funds (SoF) is missing, status is PENDING (require escrow).\n"
        "2. If SoF is present, status is PASS.\n"
        "3. If amount <= 1000, status is PASS.\n"
        "\n"
        "Transaction: Amount=${amount}, SoF_VC={sof_vc}, Sanctions_VC={sanctions_vc}.\n"
        "Determine the status (PASS/PENDING) and explain your reasoning concisely."
    )
    chain = prompt | llm | StrOutputParser()
    thought = chain.invoke({"amount": amount, "sof_vc": vcs["sof"], "sanctions_vc": vcs["sanctions"]})
    
    status = "PENDING"
    if "PASS" in thought and "PENDING" not in thought: # Simple keyword check, favoring strictness
        status = "PASS"
    if vcs["sof"]: # Hard overwrite for correctness in demo if LLM hallucinates
        status = "PASS"
    elif amount > 1000:
        status = "PENDING"

    return {
        "compliance_status": status,
        "active_agent": "CA",
        "current_thought": thought
    }

def node_propose_escrow(state: GraphState):
    """Compliance Agent: Proposes split."""
    print("--- COMPLIANCE AGENT: PROPOSING ESCROW ---")
    amount = state["buyer_intent"]["amount"]
    
    # 20/80 Split Logic
    upfront = amount * 0.2
    escrow = amount * 0.8
    
    # LLM Proposal Generation
    prompt = ChatPromptTemplate.from_template(
        "You are a Compliance Agent. The transaction amount ${amount} is high risk. "
        "Propose a split payment: 20% (${upfront}) upfront and 80% (${escrow}) in x402 smart escrow "
        "until Source of Funds is provided. Write a professional proposal message."
    )
    chain = prompt | llm | StrOutputParser()
    thought = chain.invoke({"amount": amount, "upfront": upfront, "escrow": escrow})
    
    proposal = f"Escrow Proposal: Pay ${upfront:.2f} (20%) directly, lock ${escrow:.2f} (80%) in Escrow."
    
    return {
        "active_agent": "CA",
        "current_thought": thought,
        "negotiation_log": [f"CA: {proposal}"]
    }

def node_negotiate_acceptance(state: GraphState):
    """Buyer Agent: Accepts the proposal."""
    print("--- BUYER AGENT: ACCEPTING ---")
    
    # LLM Decision
    prompt = ChatPromptTemplate.from_template(
        "You are a Buyer Agent. You have been offered an escrow split (20% now, 80% later). "
        "You value privacy but want the item. Decide to accept the proposal to move forward. "
        "Explain your reasoning (accepting the trade-off)."
    )
    chain = prompt | llm | StrOutputParser()
    thought = chain.invoke({})
    
    return {
        "active_agent": "BA",
        "current_thought": thought,
        "negotiation_log": ["BA: Proposal Accepted. Proceeding to smart contract."]
    }

def node_execute_escrow(state: GraphState):
    """Mock Ledger: Executes the split."""
    print("--- LEDGER: EXECUTING ESCROW ---")
    ledger = state["ledger"]
    amount = state["buyer_intent"]["amount"]
    
    upfront = amount * 0.2
    escrow = amount * 0.8
    
    # Move funds
    # Buyer pays full amount (split between seller and escrow)
    ledger = mock_ledger_transfer(ledger, "buyer", "seller", upfront)
    ledger = mock_ledger_transfer(ledger, "buyer", "escrow", escrow)
    
    thought = f"Smart Contract Executed. Seller received ${upfront}. Escrow holding ${escrow}."
    
    return {
        "ledger": ledger,
        "compliance_status": "ESCROW_ACTIVE",
        "active_agent": "LEDGER",
        "current_thought": thought,
        "negotiation_log": ["Chain: Tx confirmed. Funds Locked."]
    }

def node_finalize_settlement(state: GraphState):
    """Compliance Agent: Finalizes after SoF."""
    print("--- COMPLIANCE AGENT: FINALIZING ---")
    ledger = state["ledger"]
    amount = state["buyer_intent"]["amount"]
    escrow_amt = amount * 0.8
    
    # Release escrow to seller
    ledger = mock_ledger_transfer(ledger, "escrow", "seller", escrow_amt)
    
    # LLM Confirmation
    prompt = ChatPromptTemplate.from_template(
        "You are a Compliance Agent. The Source of Funds document has been provided and verified. "
        "Release the funds from escrow to the seller. State that the transaction is now fully compliant."
    )
    chain = prompt | llm | StrOutputParser()
    thought = chain.invoke({})
    
    return {
        "ledger": ledger,
        "compliance_status": "PASS",
        "active_agent": "CA",
        "current_thought": thought,
        "negotiation_log": ["CA: Compliance Met. Funds Released."]
    }

# --- routing logic ---

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
app_graph = build_graph().compile(checkpointer=memory, interrupt_after=["execute_escrow"])

if __name__ == "__main__":
    # Quick Test
    initial_state = {
        "messages": [HumanMessage(content="I want a $1500 luxury watch")],
        "ledger": {"buyer_balance": 10000, "seller_balance": 0, "escrow_balance": 0},
        "buyer_intent": {},
        "seller_offer": {},
        "compliance_status": "init",
        "active_agent": "system",
        "negotiation_log": [],
        "current_thought": "init"
    }
    
    config = {"configurable": {"thread_id": "test_1"}}
    
    print("Starting Graph...")
    for event in app_graph.stream(initial_state, config=config):
        for key, value in event.items():
            print(f"Finished: {key}")
            print(f"State: {value.get('current_thought')}")
            
    print("Graph Paused (Expected at ESCROW_ACTIVE). Resuming with SoF...")
    
    # Update state to simulate SoF upload
    # We need to manually invoke the next step or update state
    # For this simple graph, we can just call finalize directly or continue
    
    # In a real app we'd update state:
    app_graph.update_state(config, {"buyer_intent": {"amount": 1500, "attached_vcs": {"sanctions": True, "sof": True}}}, as_node="execute_escrow")
    
    # Now run the final node
    # Since we don't have a direct edge from execute_escrow to finalize (it stopped), we can add one or run it explicitly. 
    # For the `app.py`, we will need to handle this.
    # Let's Modify the graph construction slightly to allow easier resumption if we want it automatic.
    # But for now, we can just invoke the specific node or create a new run starting there.
