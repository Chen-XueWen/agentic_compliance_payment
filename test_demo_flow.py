

from langchain_core.messages import HumanMessage
import time
import sys

# Instructions:
# 1. Start Anvil: `anvil`
# 2. Deploy Contracts: `forge script script/DeployDemoSuite.s.sol --broadcast --rpc-url http://127.0.0.1:8545 --private-key $COMPLIANCE_PK`
# 3. Copy output to `deployed_addresses.json` (or ensure script does it)
# 4. Run this test: `python test_demo_flow.py`


from src.graph import app_graph
from src.state import GraphState
from src.config import ADDRS
from src.blockchain.client import w3
from src.blockchain import abis

def test_full_compliance_flow():
    """Calculates the full compliance flow integration test."""
    print("\n--- Starting End-to-End Compliance Demo Test ---")
    
    config = {"configurable": {"thread_id": f"test_{int(time.time())}"}}
    
    # 1. Buyer Request (> 1000)
    initial_inputs = {
        "messages": [HumanMessage(content="I want a $1500 luxury watch")],
        "ledger": {"buyer_balance": 10000, "seller_balance": 0, "escrow_balance": 0},
        "buyer_intent": {},
        "seller_offer": {},
        "compliance_status": "init",
        "active_agent": "system",
        "negotiation_log": [],
        "current_thought": "init",
        "transaction_id": ""
    }
    
    print("[1] Submitting Buyer Request...")
    # Run until interrupt (propose_escrow)
    # We expect the graph to stop at PENDING/propose_escrow
    
    current_state = None
    for event in app_graph.stream(initial_inputs, config=config):
        for k, v in event.items():
            current_state = v
            if isinstance(v, dict):
                print(f"Node: {k}, Status: {v.get('compliance_status')}")
            else:
                print(f"Node: {k}, Value: {v}")
            
    # Check state at interrupt
    snapshot = app_graph.get_state(config)
    state = snapshot.values
    print(f"State after interrupt: {state.get('compliance_status')}")
    
    # Needs web3 to be real PENDING, otherwise mock logic might PASS/PENDING based on logic
    # In my code, >1000 = PENDING.
    
    if state.get("compliance_status") == "PASS":
        print("WARNING: Transaction passed immediately? (Did you set threshold correctly?)")
        # If passed, we can't test escrow. 
        # But let's assume it PENDING.
    
    # 2. Accept Escrow (Resume)
    print("\n[2] Accepting Escrow Alternative...")
    # Resume graph
    # It should go propose_escrow -> negotiate -> execute -> INTERRUPT
    for event in app_graph.stream(None, config=config):
         for k, v in event.items():
            if isinstance(v, dict):
                print(f"Node: {k}, Thought: {v.get('current_thought', '')[:50]}...")
            else:
                print(f"Node: {k}, Value: {v}")

    snapshot = app_graph.get_state(config)
    state = snapshot.values
    print(f"State after Escrow Execution: {state.get('compliance_status')}")
    assert state.get("compliance_status") == "ESCROW_ACTIVE"
    
    # Verify On-chain State (if connected)
    if w3 and w3.is_connected() and ADDRS:
        print("[Chain] Verifying Balances...")
        ledger = state.get("ledger")
        print(f"Buyer: {ledger['buyer_balance']}, Escrow: {ledger['escrow_balance']}")
        # Buyer started 10000 (mock) or 3000 (chain)
        # 1500 total. 300 paid. 1200 escrow.
        # If chain used, balances should reflect.
    
    # 3. Upload SoF (Update State + Resume)
    print("\n[3] Uploading Source of Funds...")
    app_graph.update_state(
        config, 
        {"buyer_intent": {"amount": 1500, "attached_vcs": {"sanctions": True, "sof": True}}}, 
        as_node="execute_escrow"
    )
    
    for event in app_graph.stream(None, config=config):
        for k, v in event.items():
            print(f"Node: {k}, Status: {v.get('compliance_status')}")

    snapshot = app_graph.get_state(config)
    final_state = snapshot.values
    
    print(f"Final Status: {final_state.get('compliance_status')}")
    assert final_state.get("compliance_status") == "PASS"
    print("--- Test Completed Successfully ---")

if __name__ == "__main__":
    test_full_compliance_flow()
