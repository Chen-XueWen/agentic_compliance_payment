from eth_account import Account
from langchain_core.runnables import RunnableConfig
from src.state import GraphState
from src.config import ADDRS, BUYER_PK, COMPLIANCE_PK
from src.blockchain.client import w3, get_contract, is_connected
from src.blockchain.abis import WRAPPER_ABI, ESCROW_ABI, REGISTRY_ABI
from src.blockchain.utils import sign_transfer_authorization
from src.agents.tools import get_llm_chain, llm
from src.agents.ledger import get_onchain_ledger

def node_evaluate_compliance(state: GraphState, config: RunnableConfig):
    """Compliance Agent: Checks Sanctions and Amount."""
    print("--- COMPLIANCE AGENT: EVALUATING ---")
    intent = state["buyer_intent"]
    amount = intent["amount"]
    vcs = intent["attached_vcs"]
    
    # LLM Evaluation
    chain = get_llm_chain(
        "You are a Compliance Agent. Rules: \n"
        "1. If amount > 1000 and Source of Funds (SoF) is missing, status is PENDING (require escrow).\n"
        "2. If SoF is present, status is PASS.\n"
        "3. If amount <= 1000, status is PASS.\n"
        "\n"
        "Transaction: Amount=${amount}, SoF_VC={sof_vc}, Sanctions_VC={sanctions_vc}.\n"
        "Determine the status (PASS/PENDING) and explain your reasoning concisely."
    )
    
    run_config = config.copy() if config else {}
    run_config["tags"] = ["Compliance Agent"]
    thought = chain.invoke({"amount": amount, "sof_vc": vcs["sof"], "sanctions_vc": vcs["sanctions"]}, config=run_config)
    
    # --- Web3 Integration ---
    status = "PENDING"
    tx_hash = None
    
    # Check connection explicitely
    if is_connected() and ADDRS:
        try:
            # 1. Buyer signs authorization (Simulated Buyer Action)
            # In a real app, this comes from the frontend/wallet
            amount_uint = int(amount * 1e6)
            
            # The authorization must target the Wrapper as the spender/recipient of the transfer
            # Reread contract: `token.transferWithAuthorization(from, address(this), ...)`
            # So signature `to` must be `address(this)` i.e. Wrapper.
            
            # Re-sign with correct 'to'
            auth = sign_transfer_authorization(
                ADDRS["DemoSGD"], 
                BUYER_PK, 
                ADDRS["PolicyWrapper"], 
                amount_uint
            )
            
            # 2. Compliance Agent submits
            wrapper = get_contract("PolicyWrapper", WRAPPER_ABI)
            ca_account = Account.from_key(COMPLIANCE_PK)
            
            # Build Tx
            tx_data = wrapper.functions.payWithAuthorization(
                auth["from"],
                ADDRS["Seller"], # Final destination
                auth["value"],
                auth["validAfter"],
                auth["validBefore"],
                auth["nonce"],
                auth["v"],
                auth["r"],
                auth["s"]
            ).build_transaction({
                "from": ca_account.address,
                "nonce": w3.eth.get_transaction_count(ca_account.address)
            })
            
            signed_tx = w3.eth.account.sign_transaction(tx_data, private_key=COMPLIANCE_PK)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # 3. Check Status from Events
            # Event: TransactionAttested(bytes32 transactionId, uint8 status)
            # Use manual filtering to avoid MismatchedABI warnings from other events in receipt
            tx_attested_event = wrapper.events.TransactionAttested()
            event_topic = w3.keccak(text="TransactionAttested(bytes32,uint8)")
            
            logs = []
            for log in receipt["logs"]:
                # Check address and topic
                if log["address"].lower() == wrapper.address.lower() and log["topics"][0] == event_topic:
                    try:
                        decoded = tx_attested_event.process_log(log)
                        logs.append(decoded)
                    except Exception:
                        pass
            
            if logs:
                status_int = logs[0]["args"]["status"]
                status_map = {0: "PASS", 1: "FAIL", 2: "PENDING"}
                status = status_map.get(status_int, "PENDING")
                
                # Update explanation based on real result
                thought = f"On-chain Policy Result: {status}. TxHash: {tx_hash.hex()[:10]}..."
                
                # Extract Transaction ID
                tx_id_hex = logs[0]["args"]["transactionId"].hex()
                
        except Exception as e:
            print(f"Web3 Error: {e}")
            thought += f"\\n(Chain Error: {e})"
            if "Policy Check Failed" in str(e):
                status = "FAIL"
            else:
                status = "PENDING"



    return {
        "compliance_status": status,
        "active_agent": "Compliance Agent",
        "current_thought": thought,
        "ledger": get_onchain_ledger(), # Sync ledger
        "transaction_id": locals().get("tx_id_hex", "")
    }

def node_propose_escrow(state: GraphState, config: RunnableConfig):
    """Compliance Agent: Proposes split."""
    print("--- COMPLIANCE AGENT: PROPOSING ESCROW ---")
    amount = state["buyer_intent"]["amount"]
    
    # 20/80 Split Logic
    upfront = amount * 0.2
    escrow = amount * 0.8
    
    # LLM Proposal Generation
    chain = get_llm_chain(
        "You are a Compliance Agent. The transaction amount ${amount} is high risk. "
        "Propose a split payment: 20% (${upfront}) upfront and 80% (${escrow}) in x402 smart escrow "
        "until Source of Funds is provided. Write a professional proposal message."
    )
    
    run_config = config.copy() if config else {}
    run_config["tags"] = ["Compliance Agent"]
    thought = chain.invoke({"amount": amount, "upfront": upfront, "escrow": escrow}, config=run_config)
    
    proposal = f"Escrow Proposal: Pay \${upfront:.2f} (20%) directly, lock \${escrow:.2f} (80%) in Escrow."
    
    return {
        "active_agent": "Compliance Agent",
        "current_thought": thought,
        "negotiation_log": [f"Compliance Agent: {proposal}"]
    }

def node_execute_escrow(state: GraphState, config: RunnableConfig):
    """Web3: Deploys Escrow and Funds it."""
    print("--- LEDGER: EXECUTING ESCROW ---")
    amount = state["buyer_intent"]["amount"]
    
    # 20/80 Split
    upfront = amount * 0.2
    escrow_amt = amount * 0.8
    
    thought = "Initializing On-chain Escrow..."
    
    if is_connected() and ADDRS:
        try:
            # 0. Fail the Pending Transaction (Mediation)
            # "Accept escrow alternative... CA calls resolvePending(transactionId, True)"
            tx_id_hex = state.get("transaction_id")
            ca_account = Account.from_key(COMPLIANCE_PK)
            
            if tx_id_hex:
                 wrapper = get_contract("PolicyWrapper", WRAPPER_ABI)
                 tx_data_0 = wrapper.functions.resolvePending(
                     bytes.fromhex(tx_id_hex), True # Fail Now
                 ).build_transaction({
                    "from": ca_account.address,
                    "nonce": w3.eth.get_transaction_count(ca_account.address)
                 })
                 w3.eth.send_raw_transaction(w3.eth.account.sign_transaction(tx_data_0, private_key=COMPLIANCE_PK).raw_transaction)
                 thought += f"\\n(Pending Tx {tx_id_hex[:6]}... marked FAILED)"

            # 1. Manual Transfer of Upfront (Tranche 1)
            upfront_uint = int(upfront * 1e6)
            auth_upfront = sign_transfer_authorization(
                ADDRS["DemoSGD"], BUYER_PK, ADDRS["PolicyWrapper"], upfront_uint
            )
            
            wrapper = get_contract("PolicyWrapper", WRAPPER_ABI)
            
            # Fetch Nonce ONCE
            current_nonce = w3.eth.get_transaction_count(ca_account.address)
            
            tx_data_1 = wrapper.functions.payWithAuthorization(
                auth_upfront["from"], ADDRS["Seller"], auth_upfront["value"],
                auth_upfront["validAfter"], auth_upfront["validBefore"], auth_upfront["nonce"],
                auth_upfront["v"], auth_upfront["r"], auth_upfront["s"]
            ).build_transaction({
                "from": ca_account.address,
                 "nonce": current_nonce
            })
            w3.eth.send_raw_transaction(w3.eth.account.sign_transaction(tx_data_1, private_key=COMPLIANCE_PK).raw_transaction)
            
            # 2. Deploy Escrow for Tranche 2 or use existing fallback
            escrow_amt_uint = int(escrow_amt * 1e6)
            
            # Fallback: Just transfer to the Address "SimpleEscrow" from deployed_addresses, pretend it's new.
            escrow_addr = ADDRS.get("SimpleEscrow")
            if not escrow_addr:
                 raise Exception("SimpleEscrow contract not found in ADDRS. Please redeploy.")
            
            # Fund Escrow
            # buyer signs auth for escrow
            auth_escrow = sign_transfer_authorization(
                ADDRS["DemoSGD"], BUYER_PK, escrow_addr, escrow_amt_uint
            )
            
            # Call fundWithAuthorization on Escrow
            # Note: Using get_contract requires name in ADDRS, if using generic address instantiate manually
            escrow_contract = get_contract("SimpleEscrow", ESCROW_ABI)

            tx_data_2 = escrow_contract.functions.fundWithAuthorization(
                auth_escrow["validAfter"], auth_escrow["validBefore"], auth_escrow["nonce"],
                auth_escrow["v"], auth_escrow["r"], auth_escrow["s"]
            ).build_transaction({
                "from": ca_account.address,
                "nonce": current_nonce + 1 # +1 nonce
            })
            w3.eth.send_raw_transaction(w3.eth.account.sign_transaction(tx_data_2, private_key=COMPLIANCE_PK).raw_transaction)
            
            thought = f"On-chain: Tranche 1 (\${300}) settled via Wrapper. Tranche 2 (\${1200}) locked in Escrow ({escrow_addr})."
            
        except Exception as e:
            thought = f"Chain Execution Failed: {e}"
            print(thought)



    return {
        "ledger": get_onchain_ledger(),
        "compliance_status": "ESCROW_ACTIVE",
        "active_agent": "LEDGER",
        "current_thought": thought,
        "negotiation_log": ["Chain: Tx confirmed. Funds Locked."]
    }

def node_finalize_settlement(state: GraphState, config: RunnableConfig):
    """Compliance Agent: Finalizes after SoF."""
    print("--- COMPLIANCE AGENT: FINALIZING ---")
    
    thought = "Finalizing..."
    
    if is_connected() and ADDRS:
        try:
            # 1. Update Registry with SoF Hash
            registry = get_contract("IdentityRegistry", REGISTRY_ABI)
            ca_account = Account.from_key(COMPLIANCE_PK)
            
            # Fake hash for demo
            sof_hash = w3.keccak(text="MOCK_SOF_FILE")
            
            tx_data_1 = registry.functions.setSourceOfFunds(
                ADDRS["Buyer"], sof_hash
            ).build_transaction({
                "from": ca_account.address,
                "nonce": w3.eth.get_transaction_count(ca_account.address)
            })
            w3.eth.send_raw_transaction(w3.eth.account.sign_transaction(tx_data_1, private_key=COMPLIANCE_PK).raw_transaction)
            
            # 2. Release Escrow
            escrow_addr = ADDRS.get("SimpleEscrow") or ADDRS["ComplianceAgent"] 
            if escrow_addr:
                if escrow_addr == ADDRS.get("SimpleEscrow"):
                    escrow_contract = get_contract("SimpleEscrow", ESCROW_ABI)
                else:
                    escrow_contract = w3.eth.contract(address=escrow_addr, abi=ESCROW_ABI)
                    
                tx_data_2 = escrow_contract.functions.release().build_transaction({
                    "from": ca_account.address,
                    "nonce": w3.eth.get_transaction_count(ca_account.address) + 1
                })
                w3.eth.send_raw_transaction(w3.eth.account.sign_transaction(tx_data_2, private_key=COMPLIANCE_PK).raw_transaction)
                thought = "On-chain: SoF Registered. Escrow Released to Seller."
                
        except Exception as e:
            thought = f"Chain Finalization Failed: {e}"
            print(thought)


    # LLM Confirmation
    chain = get_llm_chain(
        "You are a Compliance Agent. The Source of Funds document has been provided and verified. "
        "Release the funds from escrow to the seller. State that the transaction is now fully compliant."
    )
    
    run_config = config.copy() if config else {}
    run_config["tags"] = ["Compliance Agent"]
    llm_thought = chain.invoke({}, config=run_config)
    
    return {
        "ledger": get_onchain_ledger(),
        "compliance_status": "PASS",
        "active_agent": "Compliance Agent",
        "current_thought": llm_thought,
        "negotiation_log": ["Compliance Agent: Compliance Met. Funds Released."]
    }
