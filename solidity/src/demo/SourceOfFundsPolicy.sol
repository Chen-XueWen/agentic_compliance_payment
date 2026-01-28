// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./IPolicySimple.sol";
import "./DemoIdentityRegistry.sol";

contract SourceOfFundsPolicy is IPolicySimple {
    uint256 public threshold;
    bytes32 public constant POLICY_ID = keccak256("SOURCE_OF_FUNDS_POLICY");
    bytes32 public constant REASON_MISSING = "MISSING_SOURCE_OF_FUNDS";

    constructor(uint256 _threshold) {
        threshold = _threshold;
    }

    function policyId() external pure override returns (bytes32) {
        return POLICY_ID;
    }

    function evaluate(TxContext calldata ctx, address identityRegistry)
        external
        view
        override
        returns (PolicyResult memory)
    {
        // If amount <= threshold, PASS
        if (ctx.amount <= threshold) {
            return PolicyResult(POLICY_ID, Status.PASS, bytes32(0));
        }

        // Check registry
        if (DemoIdentityRegistry(identityRegistry).hasSourceOfFunds(ctx.from)) {
            return PolicyResult(POLICY_ID, Status.PASS, bytes32(0));
        }

        // Else PENDING
        return PolicyResult(POLICY_ID, Status.PENDING, REASON_MISSING);
    }
}
