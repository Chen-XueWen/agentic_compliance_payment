from src.config import ADDRS
from src.blockchain.client import w3, get_contract
from src.blockchain.abis import DEMO_SGD_ABI

def get_onchain_ledger():
    if not w3 or not w3.is_connected():
        return {"buyer_balance": 0, "seller_balance": 0, "escrow_balance": 0}
    
    token = get_contract("DemoSGD", DEMO_SGD_ABI)
    if not token:
        return {"buyer_balance": 0, "seller_balance": 0, "escrow_balance": 0}
    
    buyer_bal = token.functions.balanceOf(ADDRS["Buyer"]).call()
    seller_bal = token.functions.balanceOf(ADDRS["Seller"]).call()
    
    # We might have multiple escrows, but for demo we track total held by contracts?
    # Or just the main ones. SimpleEscrow is created dynamically.
    # We'll just track buyer/seller for now.
    
    return {
        "buyer_balance": buyer_bal / 1e6,
        "seller_balance": seller_bal / 1e6,
        "escrow_balance": (3000 * 1e6 - buyer_bal - seller_bal) / 1e6 # Simple diff
    }
