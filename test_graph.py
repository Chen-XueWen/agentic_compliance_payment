import unittest
from langchain_core.messages import HumanMessage
from agent_graph import app_graph, GraphState

class TestAgentGraph(unittest.TestCase):
    def test_happy_path(self):
        print("\n--- Starting Happy Path Test ---")
        
        # 1. Start the Graph
        initial_inputs = {
            "messages": [HumanMessage(content="I want a $1500 luxury watch")],
            "ledger": {"buyer_balance": 10000, "seller_balance": 0, "escrow_balance": 0},
            "buyer_intent": {},
            "negotiation_log": []
        }
        config = {"configurable": {"thread_id": "test_verification_1"}}
        
        print(">> Running to Interrupt (ESCROW_ACTIVE)...")
        # Run until interrupt
        last_state = None
        for event in app_graph.stream(initial_inputs, config=config):
            for k, v in event.items():
                print(f"DEBUG: k={k}, type(v)={type(v)}")
                if isinstance(v, dict):
                    last_state = v
                    print(f"Node: {k}, Status: {v.get('compliance_status')}")
                else:
                    print(f"WARNING: Unexpected value for key {k}: {v}")

        # Verify State at Interrupt
        snapshot = app_graph.get_state(config)
        self.assertEqual(snapshot.values["compliance_status"], "ESCROW_ACTIVE")
        self.assertEqual(snapshot.values["ledger"]["escrow_balance"], 1200.0) # 80% of 1500
        self.assertEqual(snapshot.values["ledger"]["seller_balance"], 300.0)  # 20% of 1500
        self.assertEqual(snapshot.values["ledger"]["buyer_balance"], 8500.0) # 10000 - 1500
        print(">> Verified Escrow State: OK")

        # 2. Resume with Source of Funds
        print(">> Resuming with Mock SoF...")
        
        # Update state with SoF
        app_graph.update_state(
            config, 
            {"buyer_intent": {"amount": 1500, "attached_vcs": {"sanctions": True, "sof": True}}}, 
            as_node="execute_escrow"
        )
        
        # Resume execution
        final_state = None
        for event in app_graph.stream(None, config=config):
            for k, v in event.items():
                final_state = v
                print(f"Node: {k}, Status: {v.get('compliance_status')}")
                
        # Verify Final State
        snapshot = app_graph.get_state(config)
        self.assertEqual(snapshot.values["compliance_status"], "PASS")
        self.assertEqual(snapshot.values["ledger"]["escrow_balance"], 0.0)
        self.assertEqual(snapshot.values["ledger"]["seller_balance"], 1500.0) # Full amount
        print(">> Verified Final Settlement: OK")

if __name__ == "__main__":
    unittest.main()
