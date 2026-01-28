import os
import json

# --- LLM Config ---
LLM_MODEL = "gpt-oss:120b"
LLM_BASE_URL = "http://localhost:11434"

# --- Blockchain Config ---
CHAIN_ID = 31337
RPC_URL = "http://127.0.0.1:8545"

# --- Keys (Demo Only) ---
# Anvil #0: Compliance Agent (Deployer)
COMPLIANCE_PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80" 
# Anvil #1: Buyer (Has Sanctions Proof)
BUYER_PK = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
# Anvil #2: Seller
SELLER_PK = "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a"

# --- Addresses ---
def load_addresses(path="deployed_addresses.json"):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

ADDRS = load_addresses()
