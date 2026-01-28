// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./IPolicySimple.sol";

contract SimplePolicyManager {
    address public identityRegistry;
    IPolicySimple[] public policies;

    constructor(address _identityRegistry) {
        identityRegistry = _identityRegistry;
    }

    function addPolicy(address policy) external {
        policies.push(IPolicySimple(policy));
    }

    function runPolicies(IPolicySimple.TxContext calldata ctx)
        external
        view
        returns (IPolicySimple.Status overallStatus, IPolicySimple.PolicyResult[] memory results)
    {
        results = new IPolicySimple.PolicyResult[](policies.length);
        bool hasFail = false;
        bool hasPending = false;

        for (uint256 i = 0; i < policies.length; i++) {
            results[i] = policies[i].evaluate(ctx, identityRegistry);
            if (results[i].status == IPolicySimple.Status.FAIL) {
                hasFail = true;
            } else if (results[i].status == IPolicySimple.Status.PENDING) {
                hasPending = true;
            }
        }

        if (hasFail) {
            overallStatus = IPolicySimple.Status.FAIL;
        } else if (hasPending) {
            overallStatus = IPolicySimple.Status.PENDING;
        } else {
            overallStatus = IPolicySimple.Status.PASS;
        }
    }
}
