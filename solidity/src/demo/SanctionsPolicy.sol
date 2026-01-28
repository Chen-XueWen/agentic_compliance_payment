// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./IPolicySimple.sol";
import "./DemoIdentityRegistry.sol";

contract SanctionsPolicy is IPolicySimple {
    bytes32 public constant POLICY_ID = keccak256("SANCTIONS_POLICY");
    bytes32 public constant REASON_NOT_VERIFIED = "SANCTIONS_NOT_VERIFIED";

    function policyId() external pure override returns (bytes32) {
        return POLICY_ID;
    }

    function evaluate(TxContext calldata ctx, address identityRegistry)
        external
        view
        override
        returns (PolicyResult memory)
    {
        if (DemoIdentityRegistry(identityRegistry).hasSanctionsCheck(ctx.from)) {
            return PolicyResult(POLICY_ID, Status.PASS, bytes32(0));
        }
        return PolicyResult(POLICY_ID, Status.FAIL, REASON_NOT_VERIFIED);
    }
}
