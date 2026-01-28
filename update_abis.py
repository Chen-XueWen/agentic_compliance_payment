import json
import os

def load_abi(path):
    with open(path, "r") as f:
        data = json.load(f)
        return data["abi"]

sgd_abi = load_abi("out/DemoSGD.sol/DemoSGD.json")
wrapper_abi = load_abi("out/X402PolicyWrapper.sol/X402PolicyWrapper.json")
escrow_abi = load_abi("out/SimpleEscrow.sol/SimpleEscrow.json")
registry_abi = load_abi("out/DemoIdentityRegistry.sol/DemoIdentityRegistry.json")

content = f"""# Generated ABIs
DEMO_SGD_ABI = {repr(sgd_abi)}

WRAPPER_ABI = {repr(wrapper_abi)}

ESCROW_ABI = {repr(escrow_abi)}

REGISTRY_ABI = {repr(registry_abi)}
"""

with open("src/blockchain/abis.py", "w") as f:
    f.write(content)

print("src/blockchain/abis.py updated successfully.")
