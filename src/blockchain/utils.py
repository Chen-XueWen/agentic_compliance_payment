import time
import uuid
from eth_account import Account
from eth_account.messages import encode_typed_data
from src.config import CHAIN_ID
from src.blockchain.client import w3

def sign_transfer_authorization(
    token_address, 
    owner_pk, 
    to, 
    value, 
    valid_after=0, 
    valid_before=2**256 - 1, 
    nonce=None
):
    """Signs EIP-3009 TransferWithAuthorization."""
    if not w3: return None
    
    owner_account = Account.from_key(owner_pk)
    owner = owner_account.address
    
    if nonce is None:
        nonce = w3.keccak(text=str(uuid.uuid4()))

    # EIP-712 Domain
    domain = {
        "name": "Demo Singapore Dollar",
        "version": "1",
        "chainId": CHAIN_ID,
        "verifyingContract": token_address
    }
    
    # EIP-3009 Types
    types = {
        "TransferWithAuthorization": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "validAfter", "type": "uint256"},
            {"name": "validBefore", "type": "uint256"},
            {"name": "nonce", "type": "bytes32"}
        ]
    }
    
    message = {
        "from": owner,
        "to": to,
        "value": value,
        "validAfter": valid_after,
        "validBefore": valid_before,
        "nonce": nonce
    }
    
    signed = owner_account.sign_typed_data(domain, types, message)
    
    return {
        "v": signed.v,
        "r": signed.r.to_bytes(32, 'big'),
        "s": signed.s.to_bytes(32, 'big'),
        "from": owner,
        "to": to,
        "value": value,
        "validAfter": valid_after,
        "validBefore": valid_before,
        "nonce": nonce
    }
