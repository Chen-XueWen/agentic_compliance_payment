// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./DemoSGD.sol";

contract SimpleEscrow {
    DemoSGD public token;
    address public buyer;
    address public seller;
    uint256 public amount;
    uint256 public expiresAt;
    address public admin;

    bool public released;
    bool public refunded;

    event Funded(address from, uint256 amount);
    event Released(address to, uint256 amount);
    event Refunded(address to, uint256 amount);

    constructor(
        address _token,
        address _buyer,
        address _seller,
        uint256 _amount,
        uint256 _expiresAt
    ) {
        token = DemoSGD(_token);
        buyer = _buyer;
        seller = _seller;
        amount = _amount;
        expiresAt = _expiresAt;
        admin = msg.sender;
    }

    function fundWithAuthorization(
        uint256 validAfter,
        uint256 validBefore,
        bytes32 nonce,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external {
        require(!released && !refunded, "Already closed");
        token.transferWithAuthorization(buyer, address(this), amount, validAfter, validBefore, nonce, v, r, s);
        emit Funded(buyer, amount);
    }

    function release() external {
        require(msg.sender == admin, "Only admin");
        require(!released && !refunded, "Already closed");
        require(token.balanceOf(address(this)) >= amount, "Not funded");

        released = true;
        token.transfer(seller, amount);
        emit Released(seller, amount);
    }

    function refund() external {
        require(msg.sender == admin, "Only admin"); // Or expired logic
        require(!released && !refunded, "Already closed");

        refunded = true;
        uint256 balance = token.balanceOf(address(this));
        if (balance > 0) {
            token.transfer(buyer, balance);
        }
        emit Refunded(buyer, balance);
    }
}
