from brownie import chain
from helpers import RelayChain, distribute_initial_tokens
import pytest

def test_stake_collision(nimbus, oracle_master, xcTOKEN, Ledger, accounts):
    # Create 2 ledgers with shares = (10, 1000)
    stashes = [0x10, 0x20]
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)
    for i in range(len(stashes)):
        stash = stashes[i]
        nimbus.addLedger(hex(stash), hex(stash + 1), 0, {'from': accounts[0]})

    # era 0
    # deposit 1010 xcTOKEN
    deposit = 1010 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})
    nimbus.flushStakes({'from': oracle_master})
    def ledger_stakes():
        for i in range(len(stashes)):
                stash = hex(stashes[i])
                ledger = Ledger.at(nimbus.findLedger(stash))
                print('ledger ' + str(i) + ' stake = ' + str(ledger.ledgerStake() / 10**18))
        print()
    # Check current ledger stakes
    ledger_stakes()

    # era 1
    # Redeem 20 xcTOKEN
    nimbus.redeem(20 * 10**18, {'from': accounts[0]})
    # Receive report from ledger 2 with 20 rewards (Note: ledger stake doesn't increased, because 0 shares of ledger)
    nimbus.distributeRewards(20 * 10**18, 1020 * 10**18, {'from': nimbus.findLedger(stashes[1])})
    ledger_stakes()

    # era 2
    nimbus.flushStakes({'from': oracle_master})
    # check stake for ledger 1
    ledger_stakes()

    # Redeem 20 xcTOKEN
    nimbus.redeem(20 * 10**18, {'from': accounts[0]})
    # era 3
    nimbus.flushStakes({'from': oracle_master})
    # check stake for ledger 1
    ledger_stakes()
