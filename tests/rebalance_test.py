from brownie import chain
from helpers import RelayChain, distribute_initial_tokens

def test_equal_deposit_bond(nimbus, Ledger, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    relay.new_ledger("0x20", "0x21")

    ledger_1 = relay.ledgers[0]
    ledger_2 = relay.ledgers[1]

    deposit_1 = 100 * 10**18
    nimbus.deposit(deposit_1, {'from': accounts[0]})

    relay.new_era()

    assert ledger_1.free_balance == deposit_1 // 2
    assert ledger_1.active_balance == 0

    assert ledger_2.free_balance == deposit_1 // 2
    assert ledger_2.active_balance == 0

    ledgerContract_1 = Ledger.at(ledger_1.ledger_address)
    ledgerContract_2 = Ledger.at(ledger_2.ledger_address)

    for i in range(3):
        deposit_i = (i + 1) * 10 * 10**18
        nimbus.deposit(deposit_i, {'from': accounts[0]})

        reward = 2 * 10**18
        relay.new_era([reward])

        assert ledger_1.total_balance() == nimbus.ledgerBorrow(ledger_1.ledger_address)
        assert ledger_2.total_balance() == nimbus.ledgerBorrow(ledger_2.ledger_address)

    for i in range(3):
        redeem_i = (i + 1) * 10 * 10**18
        nimbus.redeem(redeem_i, {'from': accounts[0]})

        reward = 2 * 10**18
        relay.new_era([reward])

        assert ledger_1.total_balance() + ledgerContract_1.transferUpwardBalance() + ledgerContract_1.transferDownwardBalance() == nimbus.ledgerBorrow(ledger_1.ledger_address)
        assert ledger_2.total_balance() + ledgerContract_2.transferUpwardBalance() + ledgerContract_2.transferDownwardBalance() == nimbus.ledgerBorrow(ledger_2.ledger_address)


def test_direct_transfer(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    ledger_1 = relay.ledgers[0]

    deposit = 100 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    relay.new_era()

    # first redeem
    redeem = 50 * 10**18
    nimbus.redeem(nimbus.getSharesByPooledToken(redeem), {'from': accounts[0]})

    for i in range(31):
        relay.new_era()

    assert nimbus.ledgerBorrow(ledger_1.ledger_address) == deposit

    direct_transfer = 10 * 10**18
    xcTOKEN.transfer(ledger_1.ledger_address, direct_transfer, {'from': accounts[1]})

    relay.new_era()
    assert nimbus.ledgerBorrow(ledger_1.ledger_address) == deposit - redeem

    # second redeem
    nimbus.redeem(nimbus.getSharesByPooledToken(redeem), {'from': accounts[0]})

    for i in range(32):
        relay.new_era()

    assert nimbus.getTotalPooledToken() == direct_transfer + 1 # NOTE: +1 beacause of the rounding on redeem
    assert nimbus.ledgerBorrow(ledger_1.ledger_address) == direct_transfer + 1 # NOTE: +1 beacause of the rounding on redeem


def test_deposit_reward(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    nimbus.setMaxAllowableDifference(5100, {'from': accounts[0]})

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    relay.new_ledger("0x20", "0x21")
    relay.new_ledger("0x30", "0x31")
    ledger_1 = relay.ledgers[0]
    ledger_2 = relay.ledgers[1]
    ledger_3 = relay.ledgers[2]

    deposit = 90 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()

    assert ledger_1.free_balance == deposit // 3
    assert ledger_2.free_balance == deposit // 3
    assert ledger_3.free_balance == deposit // 3

    relay.new_era()

    assert ledger_1.active_balance == deposit // 3
    assert ledger_2.active_balance == deposit // 3
    assert ledger_3.active_balance == deposit // 3

    rewards = 15 * 10**18
    relay.new_era([rewards])

    assert ledger_1.active_balance == deposit // 3 + rewards
    assert ledger_2.active_balance == deposit // 3
    assert ledger_3.active_balance == deposit // 3

    deposit_2 = 3 * 10**18
    nimbus.deposit(deposit_2, {'from': accounts[0]})

    relay.new_era()

    # NOTE: see nimbus._processEnabled() to understand this distribution
    assert ledger_1.active_balance == deposit // 3 + rewards
    assert ledger_2.active_balance == deposit // 3
    assert ledger_3.active_balance == deposit // 3
    assert ledger_1.free_balance == 0
    assert ledger_2.free_balance == deposit_2 // 2
    assert ledger_3.free_balance == deposit_2 // 2

    relay.new_era()