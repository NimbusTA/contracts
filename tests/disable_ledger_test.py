from brownie import chain
from helpers import RelayChain, distribute_initial_tokens


def test_disable_ledger(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    relay.new_ledger("0x20", "0x21")

    ledger_1 = relay.ledgers[0]
    ledger_2 = relay.ledgers[1]

    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()

    assert ledger_1.free_balance == deposit // 2
    assert ledger_2.free_balance == deposit // 2

    relay.new_era()

    assert ledger_1.active_balance == deposit // 2
    assert ledger_2.active_balance == deposit // 2

    nimbus.disableLedger(ledger_2.ledger_address, {'from': accounts[0]})
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()

    assert ledger_1.active_balance == deposit // 2
    assert ledger_1.free_balance == deposit

    assert ledger_2.active_balance == deposit // 2
    assert ledger_2.free_balance == 0


def test_pause_ledger(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    relay.new_ledger("0x20", "0x21")

    ledger_1 = relay.ledgers[0]
    ledger_2 = relay.ledgers[1]

    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    relay.new_era()

    assert ledger_1.active_balance == deposit // 2
    assert ledger_2.active_balance == deposit // 2

    nimbus.emergencyPauseLedger(ledger_2.ledger_address, {'from': accounts[0]})
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    relay.new_era()

    assert ledger_1.active_balance == 3 * deposit // 2
    assert ledger_2.active_balance == deposit // 2

    nimbus.redeem(deposit, {'from': accounts[0]})

    relay.new_era()

    assert ledger_1.active_balance == deposit // 2
    assert ledger_2.active_balance == deposit // 2

    nimbus.resumeLedger(ledger_2.ledger_address, {'from': accounts[0]})

    nimbus.redeem(deposit // 2, {'from': accounts[0]})

    relay.new_era()

    assert ledger_1.active_balance == deposit // 2
    assert ledger_2.active_balance == 0