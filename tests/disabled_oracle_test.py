from brownie import chain
from helpers import RelayChain, distribute_initial_tokens


def test_deposit_redeem_with_disabled_oracle(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    relay.new_ledger("0x20", "0x21")
    relay.new_ledger("0x30", "0x31")

    deposit = 1500 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    relay.new_era()

    deposit = 600 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    # last ledger didn't receive funds from Nimbus because oracle didn't reach quorum
    relay.new_era(blocked_quorum=[False, False, True])
    assert xcTOKEN.balanceOf(nimbus) == 200 * 10**12

    redeem = 1200 * 10**12
    nimbus.redeem(redeem, {'from': accounts[0]})
    relay.new_era()

    # 200 xcTOKEN locked on Nimbus because oracle didn't send report last era
    assert xcTOKEN.balanceOf(nimbus) == 0

    relay.timetravel(28) # wait unbonding

    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    nimbus.claimUnbonded({'from': accounts[0]})

    assert xcTOKEN.balanceOf(withdrawal) == 0
    assert withdrawal.totalXcTokenPoolShares() == 0
    assert withdrawal.totalVirtualXcTokenAmount() == 0


def test_deposit_redeem_with_disabled_oracle_and_disabled_ledger(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    relay.new_ledger("0x20", "0x21")
    relay.new_ledger("0x30", "0x31")

    deposit = 1500 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    relay.new_era()

    deposit = 600 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    # last ledger didn't receive funds from Nimbus because oracle didn't reach quorum
    relay.new_era(blocked_quorum=[False, False, True])
    assert xcTOKEN.balanceOf(nimbus) == 200 * 10**12

    nimbus.disableLedger(relay.ledgers[2].ledger_address, {'from': accounts[0]})

    redeem = 1200 * 10**12
    nimbus.redeem(redeem, {'from': accounts[0]})
    relay.new_era()

    # 200 xcTOKEN locked on Nimbus because oracle didn't send report last era
    assert xcTOKEN.balanceOf(nimbus) == 0

    relay.timetravel(28) # wait unbonding

    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    nimbus.claimUnbonded({'from': accounts[0]})

    assert xcTOKEN.balanceOf(withdrawal) == 0
    assert withdrawal.totalXcTokenPoolShares() == 0
    assert withdrawal.totalVirtualXcTokenAmount() == 0


def test_redeem_deposit_with_disabled_oracle(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    relay.new_ledger("0x20", "0x21")
    relay.new_ledger("0x30", "0x31")

    deposit = 1500 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    relay.new_era()

    redeem = 600 * 10**12
    nimbus.redeem(redeem, {'from': accounts[0]})

    # last ledger didn't receive funds from Nimbus because oracle didn't reach quorum
    relay.new_era(blocked_quorum=[False, False, True])
    assert xcTOKEN.balanceOf(nimbus) == 0

    deposit = 900 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})
    relay.new_era()

    # 200 xcTOKEN locked on Nimbus because oracle didn't send report last era
    assert xcTOKEN.balanceOf(nimbus) == 0

    relay.timetravel(28) # wait unbonding

    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    nimbus.claimUnbonded({'from': accounts[0]})

    assert xcTOKEN.balanceOf(withdrawal) == 0
    assert withdrawal.totalXcTokenPoolShares() == 0
    assert withdrawal.totalVirtualXcTokenAmount() == 0