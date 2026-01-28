// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IPolicySimple {
    enum Status { PASS, FAIL, PENDING }

    struct PolicyResult {
        bytes32 policyId;
        Status status;
        bytes32 reason;
    }

    struct TxContext {
        address token;
        address from;
        address to;
        uint256 amount;
        bytes extraData;
    }

    function evaluate(TxContext calldata ctx, address identityRegistry) external view returns (PolicyResult memory);
    function policyId() external pure returns (bytes32);
}
