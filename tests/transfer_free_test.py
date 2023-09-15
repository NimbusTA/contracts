from brownie import chain
from helpers import RelayChain, distribute_initial_tokens
import pytest


def test_deposit_distribution_1(nimbus, oracle_master, xcTOKEN, Ledger, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    nimbus_balance = 100 * 10**12
    xcTOKEN.transfer(nimbus, nimbus_balance, {'from': accounts[0]})

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)

    stashes = [0x10, 0x20, 0x30, 0x40]

    for i in range(len(stashes)):
        stash = stashes[i]
        relay.new_ledger(hex(stash), hex(stash + 1))

    relay.new_era()

    # working system for 4 ledgers
    deposit = 20000 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance
    relay.new_era()

    assert relay.ledgers[0].free_balance == 0
    assert relay.ledgers[0].active_balance == deposit // 4

    # adding new ledger
    stash = 0x50
    relay.new_ledger(hex(stash), hex(stash + 1))

    relay.new_era()

    # redeem
    redeem = 4000 * 10**12
    nimbus.redeem(redeem, {'from': accounts[0]})
    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance

    assert relay.ledgers[0].free_balance == 0
    assert relay.ledgers[0].active_balance == (deposit - redeem) // 4

    # another deposit
    deposit_2 = 10000 * 10**12
    nimbus.deposit(deposit_2, {'from': accounts[0]})
    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance

    assert relay.ledgers[4].free_balance == (deposit + deposit_2 - redeem) // 5

    ledger_free = (deposit + deposit_2 - redeem) // 5 - deposit // 4
    assert relay.ledgers[0].free_balance == ledger_free
    assert relay.ledgers[0].active_balance == deposit // 4

    # redeem
    redeem_2 = 5000 * 10**12
    nimbus.redeem(redeem_2, {'from': accounts[0]})
    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance

    ledger = Ledger.at(relay.ledgers[0].ledger_address)
    assert ledger.transferDownwardBalance() == ledger_free

    # deposit
    deposit_3 = 5000 * 10**12
    nimbus.deposit(deposit_3, {'from': accounts[0]})

    for i in range(5):
        print(str(Ledger.at(relay.ledgers[i].ledger_address).transferDownwardBalance()))
    
    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance


def test_deposit_distribution_2(nimbus, oracle_master, xcTOKEN, Ledger, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    nimbus_balance = 100 * 10**12
    xcTOKEN.transfer(nimbus, nimbus_balance, {'from': accounts[0]})

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)

    stashes = [0x10, 0x20, 0x30, 0x40]

    for i in range(len(stashes)):
        stash = stashes[i]
        relay.new_ledger(hex(stash), hex(stash + 1))

    relay.new_era()

    # working system for 4 ledgers
    deposit = 20000 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance
    relay.new_era()

    assert relay.ledgers[0].free_balance == 0
    assert relay.ledgers[0].active_balance == deposit // 4

    # adding new ledger
    stash = 0x50
    relay.new_ledger(hex(stash), hex(stash + 1))

    relay.new_era()

    # redeem
    redeem = 4000 * 10**12
    nimbus.redeem(redeem, {'from': accounts[0]})
    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance

    assert relay.ledgers[0].free_balance == 0
    assert relay.ledgers[0].active_balance == (deposit - redeem) // 4

    # another deposit
    deposit_2 = 10000 * 10**12
    nimbus.deposit(deposit_2, {'from': accounts[0]})
    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance

    assert relay.ledgers[4].free_balance == (deposit + deposit_2 - redeem) // 5

    ledger_free = (deposit + deposit_2 - redeem) // 5 - deposit // 4
    assert relay.ledgers[0].free_balance == ledger_free
    assert relay.ledgers[0].active_balance == deposit // 4

    # redeem
    redeem_2 = 5000 * 10**12
    nimbus.redeem(redeem_2, {'from': accounts[0]})
    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance

    ledger = Ledger.at(relay.ledgers[0].ledger_address)
    assert ledger.transferDownwardBalance() == ledger_free

    # deposit
    deposit_3 = 10 * 10**12
    nimbus.deposit(deposit_3, {'from': accounts[0]})

    for i in range(5):
        print(str(Ledger.at(relay.ledgers[i].ledger_address).transferDownwardBalance()))
    
    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance


def test_deposit_distribution_3(nimbus, oracle_master, xcTOKEN, Ledger, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    nimbus_balance = 100 * 10**12
    xcTOKEN.transfer(nimbus, nimbus_balance, {'from': accounts[0]})

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)

    stashes = [0x10, 0x20, 0x30, 0x40]

    for i in range(len(stashes)):
        stash = stashes[i]
        relay.new_ledger(hex(stash), hex(stash + 1))

    relay.new_era()

    # working system for 4 ledgers
    deposit = 20000 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance
    relay.new_era()

    assert relay.ledgers[0].free_balance == 0
    assert relay.ledgers[0].active_balance == deposit // 4

    # adding new ledger
    stash = 0x50
    relay.new_ledger(hex(stash), hex(stash + 1))

    relay.new_era()

    # redeem
    redeem = 4000 * 10**12
    nimbus.redeem(redeem, {'from': accounts[0]})
    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance

    assert relay.ledgers[0].free_balance == 0
    assert relay.ledgers[0].active_balance == (deposit - redeem) // 4

    # another deposit
    deposit_2 = 10000 * 10**12
    nimbus.deposit(deposit_2, {'from': accounts[0]})
    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance

    assert relay.ledgers[4].free_balance == (deposit + deposit_2 - redeem) // 5

    ledger_free = (deposit + deposit_2 - redeem) // 5 - deposit // 4
    assert relay.ledgers[0].free_balance == ledger_free
    assert relay.ledgers[0].active_balance == deposit // 4

    # redeem
    redeem_2 = 5000 * 10**12
    nimbus.redeem(redeem_2, {'from': accounts[0]})
    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance

    ledger = Ledger.at(relay.ledgers[0].ledger_address)
    assert ledger.transferDownwardBalance() == ledger_free

    # deposit
    deposit_3 = 4500 * 10**12
    nimbus.deposit(deposit_3, {'from': accounts[0]})

    for i in range(5):
        print(str(Ledger.at(relay.ledgers[i].ledger_address).transferDownwardBalance()))
    
    relay.new_era()
    assert xcTOKEN.balanceOf(nimbus) == nimbus_balance