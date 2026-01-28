import json
from langchain_core.runnables import RunnableConfig
from src.state import GraphState
from src.agents.tools import get_llm_chain, llm

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

    buyer_intent = {
        "item": item,
        "amount": amount,
        "attached_vcs": {"sanctions": True, "sof": False}
    }
    
    # LLM Call for Thought
    thought_chain = get_llm_chain(
        "You are a Buyer Agent. You processed a request for '{item}' at ${amount}. "
        "You have a Sanctions VC but NO Source of Funds VC. "
        "Think aloud about your current status and what you are submitting."
    )
    
    # Merge config with tags
    run_config = config.copy() if config else {}
    run_config["tags"] = ["Buyer Agent"]
    thought = thought_chain.invoke({"item": item, "amount": amount}, config=run_config)
    
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
