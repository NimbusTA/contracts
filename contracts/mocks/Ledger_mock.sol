// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
pragma abicoder v2;

import "../../interfaces/INimbus.sol";

contract LedgerMock {
    INimbus public NIMBUS;

    function initialize(
        bytes32 _stashAccount,
        bytes32 _controllerAccount,
        address _xcTOKEN,
        address _controller,
        uint128 _minNominatorBalance,
        address _nimbus,
        uint128 _minimumBalance,
        uint256 _maxUnlockingChunks
    ) external {
        NIMBUS = INimbus(_nimbus);
    }

    function distributeRewards(uint256 _totalRewards, uint256 _balance) external {
        NIMBUS.distributeRewards(_totalRewards, _balance);
    }
}
