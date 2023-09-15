// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./proxy/LedgerProxy.sol";
import "../interfaces/ILedger.sol";

contract LedgerFactory {
    // Nimbus address
    address private immutable NIMBUS;

    // Ledger beacon address
    address private immutable LEDGER_BEACON;

    /**
    * @notice Constructor
    * @param _nimbus - Nimbus address
    * @param _ledgerBeacon - ledger beacon address
    */
    constructor(address _nimbus, address _ledgerBeacon) {
        require(_nimbus != address(0), "LF: NIMBUS_ZERO_ADDRESS");
        require(_ledgerBeacon != address(0), "LF: BEACON_ZERO_ADDRESS");

        NIMBUS = _nimbus;
        LEDGER_BEACON = _ledgerBeacon;
    }

    /**
    * @notice Create new ledger proxy contract
    * @param _stashAccount - stash account address on relay chain
    * @param _controllerAccount - controller account on relay chain
    * @param _xcTOKEN - xcTOKEN contract address
    * @param _controller - xcmTransactor(relaychain calls relayer) contract address
    * @param _minNominatorBalance - minimal allowed nominator balance
    * @param _minimumBalance - minimal allowed active balance for ledger
    * @param _maxUnlockingChunks - maximum amount of unlocking chunks
    */
    function createLedger(
        bytes32 _stashAccount,
        bytes32 _controllerAccount,
        address _xcTOKEN,
        address _controller,
        uint128 _minNominatorBalance,
        uint128 _minimumBalance,
        uint256 _maxUnlockingChunks
    ) external returns (address) {
        require(msg.sender == NIMBUS, "LF: ONLY_NIMBUS");

        address ledger = address(
            new LedgerProxy(
                LEDGER_BEACON,
                abi.encodeWithSelector(
                    ILedger.initialize.selector,
                    _stashAccount,
                    _controllerAccount,
                    _xcTOKEN,
                    _controller,
                    _minNominatorBalance,
                    NIMBUS,
                    _minimumBalance,
                    _maxUnlockingChunks
                )
            )
        );

        return ledger;
    }
}