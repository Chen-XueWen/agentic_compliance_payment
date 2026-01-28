from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage
import operator

class GraphState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    buyer_intent: dict      # {item, amount, attached_vcs: {sanctions: bool, sof: bool}}
    seller_offer: dict      # {sku, price, jurisdiction}
    compliance_status: str  # "PASS", "FAIL", "PENDING", "ESCROW_ACTIVE"
    active_agent: str       # "Buyer Agent", "Seller Agent", or "Compliance Agent"
    negotiation_log: List[str]   # List of structured proposals/logs
    ledger: dict            # {buyer_balance, seller_balance, escrow_balance}
    current_thought: str    # The "internal monologue" of the active agent
    transaction_id: str     # Hex string of current tx ID
