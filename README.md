# Agentic Compliance Payment System

![Solution Architecture](./SolutionImage.png)

An intelligent payment system that uses AI Agents (LangGraph) and On-Chain Contracts (Solidity) to enforce programmable compliance. This demo showcases a workflow where a Compliance Agent mediates a high-value transaction using a Smart Escrow when Source of Funds (SoF) is missing.

## Features

- **Multi-Agent Workflow**: Buyer, Seller, and Compliance Agents interact to negotiate and settle transactions.
- **On-Chain Programmable Compliance**: Solidity contracts implement the [Global Layer One Programmable Compliance framework](https://doc.global-layer-one.org/docs/programmable-compliance/reference-model/overview), with `X402PolicyWrapper` serving as the x402-compatible entry point for policy evaluation, attestation, and conditional settlement on a local Ethereum blockchain.
- **Programmable Mediation**: The Compliance Agent can propose and execute split payments using an escrow contract to resolve pending compliance requirements.
- **Modular Architecture**: Clean separation between agent logic (`src/agents`) and blockchain services (`src/blockchain`).

## Prerequisites

-   **Python 3.10+**
-   **Foundry** (Binaries provided in `./bin`, or install globally)
-   **Ollama** (for local LLM inference, running `gpt-oss:120b` or similar)

## Installation

1.  **Clone the repository**:
    ```bash
    git clone <repo-url>
    cd agentic_compliance_payment
    ```

2.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *(If `requirements.txt` is missing, install: `langchain langgraph langchain-ollama web3 streamlit eth-account pydantic`)*

3.  **Ensure Ollama is running**:
    ```bash
    ollama serve
    ```

## Quick Start

### 1. Start Local Blockchain
Start the Anvil node using the included binary:
```bash
./bin/anvil
```
*Keep this terminal open.*

### 2. Deploy Contracts
In a new terminal, deploy the Solidity contracts to your local node:
```bash
./bin/forge script solidity/script/DeployDemoSuite.s.sol \
  --broadcast \
  --rpc-url http://127.0.0.1:8545 \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
  --use ./bin/solc
```

### 3. Run the Demo
You can run the interactive UI or the automated test script.

**Option A: Interactive UI (Streamlit)**
```bash
streamlit run app.py
```
Open a browser to the provided URL (usually `http://localhost:8501`).

**Option B: Automated Verification**
Run the end-to-end integration test:
```bash
python test_demo_flow.py
```

## Project Structure

```
.
├── app.py                  # Streamlit Frontend
├── test_demo_flow.py       # E2E Logic Test
├── src/
│   ├── agents/             # Agent Logic (Buyer, Compliance, Ledger)
│   ├── blockchain/         # Web3 Client & ABIs
│   ├── config.py           # Configuration (Keys, URLs)
│   ├── graph.py            # LangGraph Workflow Definition
│   └── state.py            # Shared State Types
├── bin/                    # Foundry Binaries (anvil, forge, etc.)
└── solidity/               # Smart Contracts
```
