// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract DemoIdentityRegistry {
    // Wallet -> Document Hash
    mapping(address => bytes32) public sourceOfFundsRef;
    // Wallet -> Check Hash
    mapping(address => bytes32) public sanctionsRef;

    function setSourceOfFunds(address wallet, bytes32 ref) external {
        sourceOfFundsRef[wallet] = ref;
    }

    function setSanctionsCheck(address wallet, bytes32 ref) external {
        sanctionsRef[wallet] = ref;
    }

    function hasSourceOfFunds(address wallet) external view returns (bool) {
        return sourceOfFundsRef[wallet] != bytes32(0);
    }

    function hasSanctionsCheck(address wallet) external view returns (bool) {
        return sanctionsRef[wallet] != bytes32(0);
    }
}
