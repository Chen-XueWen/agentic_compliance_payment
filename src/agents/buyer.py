import json
from langchain_core.runnables import RunnableConfig
from src.state import GraphState
from src.agents.tools import get_llm_chain, llm
from src.config import ADDRS
from src.blockchain.client import is_connected, get_contract
from src.blockchain.abis import REGISTRY_ABI

def node_analyze_intent(state: GraphState, config: RunnableConfig):
    """Buyer Agent: Parses user input into structured intent."""
    print("--- BUYER AGENT: ANALYZING INTENT ---")
    messages = state["messages"]
    last_message = messages[-1].content
    
    # LLM Call for Extraction
    chain = get_llm_chain(
        "Extract the item and amount from this request: '{request}'. "
        "Return JSON with keys 'item' (string) and 'amount' (float). "
        "If unsure, default to item='Unknown' and amount=0."
    )
    
    try:
        run_config = config.copy() if config else {}
        run_config["tags"] = ["Buyer Agent"]
        response = chain.invoke({"request": last_message}, config=run_config)
        
        # Basic cleanup to find JSON
        json_str = response[response.find("{"):response.rfind("}")+1]
        data = json.loads(json_str)
        item = data.get("item", "Luxury Watch")
        amount = float(data.get("amount", 1500))
    except Exception as e:
        print(f"LLM Extraction Failed: {e}")
        item = "Unknown"
        amount = 0.0

    # Credentials from Graph State (Populated at init)
    creds = state.get("buyer_credentials", {"has_sanctions": False, "has_sof": False})
    has_sanctions = creds.get("has_sanctions", False)
    has_sof = creds.get("has_sof", False)

    buyer_intent = {
        "item": item,
        "amount": amount,
        "attached_vcs": {"sanctions": has_sanctions, "sof": has_sof}
    }
    
    # LLM Call for Thought
    thought_chain = get_llm_chain(
        "You are a Buyer Agent. You processed a request for '{item}' at ${amount}. "
        "Your Wallet Status: Sanctions Verified={has_sanctions}, Source of Funds Verified={has_sof}. "
        "Think aloud about your current status and what credentials you are submitting with your transaction."
    )
    
    # Merge config with tags
    run_config = config.copy() if config else {}
    run_config["tags"] = ["Buyer Agent"]
    thought = thought_chain.invoke({
        "item": item, 
        "amount": amount,
        "has_sanctions": has_sanctions,
        "has_sof": has_sof
    }, config=run_config)
    
    return {
        "buyer_intent": buyer_intent,
        "active_agent": "Buyer Agent",
        "current_thought": thought,
        "negotiation_log": [f"Buyer Agent: Initiating purchase for {item} (${amount})."]
    }

def node_negotiate_acceptance(state: GraphState, config: RunnableConfig):
    """Buyer Agent: Accepts the proposal."""
    print("--- BUYER AGENT: ACCEPTING ---")
    
    chain = get_llm_chain(
        "You are a Buyer Agent. You have been offered an escrow split (20% now, 80% later). "
        "You value privacy but want the item. Decide to accept the proposal to move forward. "
        "Explain your reasoning (accepting the trade-off)."
    )
    
    run_config = config.copy() if config else {}
    run_config["tags"] = ["Buyer Agent"]
    thought = chain.invoke({}, config=run_config)
    
    return {
        "active_agent": "Buyer Agent",
        "current_thought": thought,
        "negotiation_log": ["Buyer Agent: Proposal Accepted. Proceeding to smart contract."]
    }
