from web3 import Web3
from src.config import RPC_URL, ADDRS
from src.blockchain import abis

try:
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
except Exception:
    w3 = None

def get_contract(name, abi):
    if w3 and w3.is_connected() and name in ADDRS:
        return w3.eth.contract(address=ADDRS[name], abi=abi)
    return None

def is_connected():
    return w3 and w3.is_connected()
