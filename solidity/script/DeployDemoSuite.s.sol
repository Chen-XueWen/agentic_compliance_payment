// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/demo/DemoSGD.sol";
import "../src/demo/DemoIdentityRegistry.sol";
import "../src/demo/SourceOfFundsPolicy.sol";
import "../src/demo/SanctionsPolicy.sol";
import "../src/demo/SimplePolicyManager.sol";
import "../src/demo/X402PolicyWrapper.sol";

contract DeployDemoSuite is Script {
    function run() external {
        // Load keys from simple env or hardcoded for demo as request implies specific keys
        // "Deploy all demo contracts using Compliance Agent key"
        // In foundry, usually we use vm.startBroadcast(privateKey)
        // I'll assume keys are provided via env or I use a derived key. 
        // For the json output, I need to know the addresses of Buyer/Seller/CA.
        // I will use some deterministic keys for the demo script or read from env.
        
        uint256 COMPLIANCE_PK = vm.envOr("COMPLIANCE_PK", uint256(0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80)); // Anvil #0
        uint256 BUYER_PK = vm.envOr("BUYER_PK", uint256(0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d));      // Anvil #1
        uint256 SELLER_PK = vm.envOr("SELLER_PK", uint256(0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a));     // Anvil #2

        address complianceAgent = vm.addr(COMPLIANCE_PK);
        address buyer = vm.addr(BUYER_PK);
        address seller = vm.addr(SELLER_PK);

        vm.startBroadcast(COMPLIANCE_PK);

        // 1. Deploy DemoSGD
        DemoSGD token = new DemoSGD();

        // 2. Deploy Registry
        DemoIdentityRegistry registry = new DemoIdentityRegistry();

        // 3. Deploy Policies
        // SourceOfFundsPolicy (threshold = 1000 * 1e6)
        SourceOfFundsPolicy sofPolicy = new SourceOfFundsPolicy(1000 * 1e6);
        
        // SanctionsPolicy
        SanctionsPolicy sanctionsPolicy = new SanctionsPolicy();

        // 4. Deploy Manager & Register Policies
        SimplePolicyManager manager = new SimplePolicyManager(address(registry));
        manager.addPolicy(address(sofPolicy));
        manager.addPolicy(address(sanctionsPolicy));

        // 5. Deploy Wrapper
        X402PolicyWrapper wrapper = new X402PolicyWrapper(address(token), address(manager));

        // 5.5 Deploy SimpleEscrow (Standalone for Demo)
        // In a real app, this is deployed per transaction. Here we deploy one shared instance.
        // We use block.timestamp + 1000 days for expiry
        import "../src/demo/SimpleEscrow.sol";
        SimpleEscrow escrow = new SimpleEscrow(address(token), buyer, seller, 1200 * 1e6, block.timestamp + 1000 days);

        // 6. Setup State
        // Mint 10000 * 1e6 to Buyer (Matches Mock)
        token.mint(buyer, 10000 * 1e6);
        
        // Set Buyer sanctions proof
        registry.setSanctionsCheck(buyer, keccak256("VALID_SANCTIONS_PROOF"));

        vm.stopBroadcast();

        // 7. Output JSON
        string memory json1 = "key1"; 
        vm.serializeAddress(json1, "DemoSGD", address(token));
        vm.serializeAddress(json1, "IdentityRegistry", address(registry));
        vm.serializeAddress(json1, "PolicyManager", address(manager));
        vm.serializeAddress(json1, "PolicyWrapper", address(wrapper));
        vm.serializeAddress(json1, "SourceOfFundsPolicy", address(sofPolicy));
        vm.serializeAddress(json1, "SanctionsPolicy", address(sanctionsPolicy));
        vm.serializeAddress(json1, "Buyer", buyer);
        vm.serializeAddress(json1, "Seller", seller);
        vm.serializeAddress(json1, "ComplianceAgent", complianceAgent);
        string memory finalJson = vm.serializeUint(json1, "ChainId", block.chainid);

        vm.writeJson(finalJson, "./deployed_addresses.json");
    }
}
