// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./DemoSGD.sol";
import "./SimplePolicyManager.sol";

contract X402PolicyWrapper {
    DemoSGD public token;
    SimplePolicyManager public policyManager;

    struct Attestation {
        IPolicySimple.Status status;
        IPolicySimple.PolicyResult[] results;
        uint256 timestamp;
    }

    mapping(bytes32 => Attestation) public attestations;
    address public admin;

    event TransactionAttested(bytes32 indexed transactionId, IPolicySimple.Status status);
    event TransactionCompleted(bytes32 indexed transactionId, address indexed from, address indexed to, uint256 amount);

    constructor(address _token, address _policyManager) {
        token = DemoSGD(_token);
        policyManager = SimplePolicyManager(_policyManager);
        admin = msg.sender;
    }

    function calculateTransactionId(
        address from,
        address to,
        uint256 amount,
        bytes32 nonce
    ) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(from, to, amount, nonce));
    }

    function payWithAuthorization(
        address from,
        address to,
        uint256 value,
        uint256 validAfter,
        uint256 validBefore,
        bytes32 nonce,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        bytes32 txId = calculateTransactionId(from, to, value, nonce);

        // 1. Build TxContext
        IPolicySimple.TxContext memory ctx = IPolicySimple.TxContext({
            token: address(token),
            from: from,
            to: to,
            amount: value,
            extraData: ""
        });

        // 2. Run Policies
        (IPolicySimple.Status status, IPolicySimple.PolicyResult[] memory results) = policyManager.runPolicies(ctx);

        // 3. Store Attestation
        Attestation storage att = attestations[txId];
        att.status = status;
        // Copy struct array is tricky in storage, need loop
        for(uint i=0; i<results.length; i++) {
            att.results.push(results[i]);
        }
        att.timestamp = block.timestamp;

        emit TransactionAttested(txId, status);

        // 4. Handle Outcome
        if (status == IPolicySimple.Status.FAIL) {
            revert("Policy Check Failed");
        } else if (status == IPolicySimple.Status.PENDING) {
            // Return without moving funds
            return;
        } else {
            // PASS: Execute Settlement
            // Custody: From -> Wrapper
            token.transferWithAuthorization(from, address(this), value, validAfter, validBefore, nonce, v, r, s);
            // Delivery: Wrapper -> To
            token.transfer(to, value);
            emit TransactionCompleted(txId, from, to, value);
        }
    }

    function resolvePending(bytes32 transactionId, bool failNow) external {
        // Simple admin check for demo
        // In reality, this might be restricted to the Compliance Agent or have more logic
        require(msg.sender == admin, "Only admin");
        
        Attestation storage att = attestations[transactionId];
        require(att.status == IPolicySimple.Status.PENDING, "Not pending");

        if (failNow) {
            att.status = IPolicySimple.Status.FAIL;
            emit TransactionAttested(transactionId, IPolicySimple.Status.FAIL);
        }
    }

    function getAttestation(bytes32 transactionId) external view returns (IPolicySimple.Status, IPolicySimple.PolicyResult[] memory) {
        Attestation storage att = attestations[transactionId];
        return (att.status, att.results);
    }
}
