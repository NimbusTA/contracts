from black import assert_equivalent
from brownie import chain
from helpers import RelayChain, distribute_initial_tokens
import pytest


def test_redeem(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit1 = 20 * 10**12
    deposit2 = 5 * 10**12
    deposit3 = 100 * 10**12
    nimbus.deposit(deposit1, {'from': accounts[0]})
    nimbus.deposit(deposit2, {'from': accounts[1]})
    nimbus.deposit(deposit3, {'from': accounts[2]})

    relay.new_era()

    reward = 3 * 10**12
    relay.new_era([reward])
    assert relay.ledgers[0].active_balance == deposit1 + deposit2 + deposit3 + reward
    assert nimbus.getTotalPooledToken() == deposit1 + deposit2 + deposit3 + reward

    balance_for_redeem = nimbus.balanceOf(accounts[1])
    balance_in_xcToken = nimbus.getPooledTokenByShares(balance_for_redeem)
    nimbus.redeem(balance_for_redeem, {'from': accounts[1]})

    relay.new_era([reward])

    # travel for 28 eras
    relay.timetravel(28) # wait unbonding

    relay.new_era([reward])  # should send 'withdraw'
    relay.new_era([reward])  # should downward transfer
    relay.new_era([reward])  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    withdrawal_xc_token = xcTOKEN.balanceOf(withdrawal)
    assert withdrawal_xc_token == balance_in_xcToken

    balance_before_claim = xcTOKEN.balanceOf(accounts[1])
    nimbus.claimUnbonded({'from': accounts[1]})

    assert xcTOKEN.balanceOf(accounts[1]) == balance_in_xcToken + balance_before_claim
    assert nimbus.getTotalPooledToken() == deposit1 + deposit2 + deposit3 + 5*reward - balance_in_xcToken


@pytest.mark.skip_coverage
def test_check_queue(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit = 20 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})
    nimbus.deposit(deposit, {'from': accounts[1]})
    nimbus.deposit(deposit, {'from': accounts[2]})
    nimbus.deposit(deposit, {'from': accounts[3]})
    nimbus.deposit(deposit, {'from': accounts[4]})

    relay.new_era()
    relay.new_era()

    assert relay.ledgers[0].active_balance == deposit * 5

    for j in range(5):
        for i in range(20):
            nimbus.redeem(10**12, {'from': accounts[j]})
            relay.new_era()

    # One more claim for check function 
    balance_before_claim = xcTOKEN.balanceOf(accounts[0])
    nimbus.claimUnbonded({'from': accounts[0]})
    balance_after_claim = xcTOKEN.balanceOf(accounts[0])

    for i in range(28):
        relay.new_era() # wait unbonding for last redeem for last user
    
    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    withdrawal_xc_token = xcTOKEN.balanceOf(withdrawal)
    diff = balance_after_claim - balance_before_claim
    assert withdrawal_xc_token == (deposit * 5 - diff)

    for i in range(1, 5):
        balance_before_claim = xcTOKEN.balanceOf(accounts[i])
        nimbus.claimUnbonded({'from': accounts[i]})
        assert xcTOKEN.balanceOf(accounts[i]) == (deposit + balance_before_claim)


def test_losses_distribution(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)
    nimbus.setMaxAllowableDifference(51000, {'from': accounts[0]})

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit = 100 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    relay.new_era()

    assert relay.ledgers[0].active_balance == deposit

    redeem = 60 * 10**12
    redeem_in_xcToken = nimbus.getPooledTokenByShares(redeem)
    nimbus.redeem(redeem, {'from': accounts[0]})
    relay.new_era()

    nimbus_virtual_balance = nimbus.fundRaisedBalance()
    withdrawal_virtual_balance = withdrawal.totalVirtualXcTokenAmount()

    assert nimbus_virtual_balance == deposit - redeem_in_xcToken
    assert withdrawal_virtual_balance == redeem_in_xcToken

    assert relay.ledgers[0].total_balance() == deposit

    losses = 51_234_567_890_377
    relay.new_era([-losses])

    assert relay.ledgers[0].total_balance() == deposit - losses
    assert nimbus.fundRaisedBalance() == 19_506_172_843_850 # fundRaisedBalance - 40% of the losses
    assert withdrawal.totalVirtualXcTokenAmount() == 29_259_259_265_773 # totalVirtualXcTokenAmount - rest of the losses

    # travel for 28 eras
    relay.timetravel(28) # wait unbonding

    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    nimbus.claimUnbonded({'from': accounts[0]})

    assert withdrawal.totalXcTokenPoolShares() == 0
    assert withdrawal.totalVirtualXcTokenAmount() == 0
    assert xcTOKEN.balanceOf(withdrawal) <= 100
    assert relay.ledgers[0].total_balance() == nimbus.fundRaisedBalance()
    assert relay.ledgers[0].active_balance == nimbus.fundRaisedBalance()

    nimbus.redeem(nimbus.balanceOf(accounts[0]), {'from': accounts[0]})
    relay.new_era()

    relay.timetravel(28) # wait unbonding

    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    nimbus.claimUnbonded({'from': accounts[0]})

    assert withdrawal.totalXcTokenPoolShares() == 0
    assert withdrawal.totalVirtualXcTokenAmount() == 0
    assert xcTOKEN.balanceOf(withdrawal) <= 100
    assert nimbus.totalSupply() == 0
    assert relay.ledgers[0].total_balance() == nimbus.fundRaisedBalance()
    assert relay.ledgers[0].active_balance == nimbus.fundRaisedBalance()


@pytest.mark.skip_coverage
def test_relay_block(nimbus, oracle_master, xcTOKEN, withdrawal, Ledger, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit = 20 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    relay.new_era()

    assert relay.ledgers[0].active_balance == deposit

    for i in range(15):
        nimbus.redeem(10**12, {'from': accounts[0]})
        relay.new_era()

    withdrawal_xc_token = xcTOKEN.balanceOf(withdrawal)
    assert withdrawal_xc_token == 0

    # Block xcm messages for 30 eras
    relay.block_xcm_messages = True
    for i in range(5):
        nimbus.redeem(10**12, {'from': accounts[0]})
        relay.new_era()
        withdrawal_xc_token = xcTOKEN.balanceOf(withdrawal)
        assert withdrawal_xc_token == 0

    # Unblock xcm messages
    relay.block_xcm_messages = False

    ledger = Ledger.at(relay.ledgers[0].ledger_address)
    assert ledger.transferDownwardBalance() == 0
    assert nimbus.ledgerStake(ledger.address) == 0

    relay.new_era()

    (waitingToUnbonding, readyToClaim) = nimbus.getUnbonded(accounts[0])

    assert readyToClaim == 0
    assert waitingToUnbonding == 20 * 10**12

    for i in range(38): # wait 33 era + 5 for eras with blocked messages
        relay.new_era() # wait unbonding for last redeem
    
    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    withdrawal_xc_token = xcTOKEN.balanceOf(withdrawal)
    assert withdrawal_xc_token == deposit

    balance_before_claim = xcTOKEN.balanceOf(accounts[0])
    nimbus.claimUnbonded({'from': accounts[0]})

    assert xcTOKEN.balanceOf(accounts[0]) == (deposit + balance_before_claim)


def test_losses_distribution_with_fast_track(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)
    nimbus.setMaxAllowableDifference(51000, {'from': accounts[0]})

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit = 100 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    relay.new_era()

    assert relay.ledgers[0].active_balance == deposit

    redeem = 60 * 10**12
    redeem_in_xcToken = nimbus.getPooledTokenByShares(redeem)
    nimbus.redeem(redeem, {'from': accounts[0]})
    relay.new_era()

    deposit_2 = 56_678_123_504_984
    nimbus.deposit(deposit_2, {'from': accounts[1]})
    relay.new_era()

    nimbus_virtual_balance = nimbus.fundRaisedBalance()
    withdrawal_virtual_balance = withdrawal.totalVirtualXcTokenAmount()

    assert nimbus_virtual_balance == deposit + deposit_2 - redeem_in_xcToken
    assert withdrawal_virtual_balance == redeem_in_xcToken

    assert relay.ledgers[0].total_balance() == deposit

    (waiting, available) = nimbus.getUnbonded(accounts[0])
    print("Waiting = " + str(waiting / 10**12))

    losses = 51_234_567_890_377
    relay.new_era([-losses])

    (waiting, available) = nimbus.getUnbonded(accounts[0])
    print("Waiting = " + str(waiting / 10**12))


    assert relay.ledgers[0].total_balance() == deposit - losses

    # travel for 28 eras
    relay.timetravel(28) # wait unbonding

    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    nimbus.claimUnbonded({'from': accounts[0]})

    assert withdrawal.totalXcTokenPoolShares() == 0
    assert withdrawal.totalVirtualXcTokenAmount() == 0
    assert xcTOKEN.balanceOf(withdrawal) <= 100
    assert relay.ledgers[0].total_balance() == nimbus.fundRaisedBalance()
    assert relay.ledgers[0].active_balance == nimbus.fundRaisedBalance()

    nimbus.redeem(nimbus.balanceOf(accounts[0]), {'from': accounts[0]})
    nimbus.redeem(nimbus.balanceOf(accounts[1]), {'from': accounts[1]})
    relay.new_era()

    relay.timetravel(28) # wait unbonding

    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    nimbus.claimUnbonded({'from': accounts[0]})
    nimbus.claimUnbonded({'from': accounts[1]})

    assert withdrawal.totalXcTokenPoolShares() == 0
    assert withdrawal.totalVirtualXcTokenAmount() == 0
    assert xcTOKEN.balanceOf(withdrawal) <= 100
    assert nimbus.totalSupply() < 10
    assert relay.ledgers[0].total_balance() == nimbus.fundRaisedBalance()
    assert relay.ledgers[0].active_balance == nimbus.fundRaisedBalance()


def test_losses_distribution_with_fast_track_2_ledgers(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)
    nimbus.setMaxAllowableDifference(51000, {'from': accounts[0]})

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    relay.new_ledger("0x20", "0x21")
    relay.new_ledger("0x30", "0x31")

    deposit = 1500 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    relay.new_era()

    redeem = 1350 * 10**12
    nimbus.redeem(redeem, {'from': accounts[0]})
    relay.new_era()

    deposit_2 = 1200 * 10**12
    nimbus.deposit(deposit_2, {'from': accounts[1]})
    relay.new_era()

    nimbus_virtual_balance = nimbus.fundRaisedBalance()
    withdrawal_virtual_balance = withdrawal.totalVirtualXcTokenAmount()

    assert nimbus_virtual_balance == deposit + deposit_2 - redeem
    assert withdrawal_virtual_balance == redeem

    (waiting, available) = nimbus.getUnbonded(accounts[0])
    print("Waiting = " + str(waiting / 10**12))

    losses = 400 * 10**12
    relay.new_era([-losses])

    (waiting, available) = nimbus.getUnbonded(accounts[0])
    print("Waiting = " + str(waiting / 10**12))

    # travel for 28 eras
    relay.timetravel(28) # wait unbonding

    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    nimbus.claimUnbonded({'from': accounts[0]})

    assert withdrawal.totalXcTokenPoolShares() == 0
    assert withdrawal.totalVirtualXcTokenAmount() == 0
    assert xcTOKEN.balanceOf(withdrawal) <= 1000
    assert relay.ledgers[0].total_balance() == 90 * 10**12
    assert relay.ledgers[0].active_balance == 90 * 10**12
    assert relay.ledgers[1].total_balance() == 450 * 10**12
    assert relay.ledgers[1].active_balance == 450 * 10**12
    assert relay.ledgers[1].total_balance() == 450 * 10**12
    assert relay.ledgers[1].active_balance == 450 * 10**12

    nimbus.redeem(nimbus.balanceOf(accounts[0]), {'from': accounts[0]})
    nimbus.redeem(nimbus.balanceOf(accounts[1]), {'from': accounts[1]})
    relay.new_era()

    relay.timetravel(28) # wait unbonding

    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    nimbus.claimUnbonded({'from': accounts[0]})
    nimbus.claimUnbonded({'from': accounts[1]})

    assert withdrawal.totalXcTokenPoolShares() == 0
    assert withdrawal.totalVirtualXcTokenAmount() == 0
    assert xcTOKEN.balanceOf(withdrawal) <= 1000
    assert nimbus.totalSupply() == 0
    assert relay.ledgers[0].total_balance() == nimbus.totalSupply()
    assert relay.ledgers[0].active_balance == nimbus.totalSupply()


def test_redeem_before_losses(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    # 1. deposit tokens
    deposit = 100 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    relay.new_era()

    assert relay.ledgers[0].active_balance == deposit

    # 1.1 first redeem to make totalXcTokenBalance on Withdrawal > 0
    redeem_1 = 55 * 10**12
    nimbus.redeem(redeem_1, {'from': accounts[0]})

    relay.new_era()

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 55 * 10**12

    # 2. add new era with loss
    relay.new_era(rewards=[-10 * 10**12], blocked_quorum=[True])

    # 3. redeem tokens before consensus is reached on the ledger
    redeem = 5 * 10**12
    nimbus.redeem(redeem, {'from': accounts[0]})

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 60 * 10**12

    # 4. reach consensus on the ledger
    relay.finalize_quorum(0)

    assert nimbus.ledgerStake(relay.ledgers[0].ledger_address) == 405 * 10**11
    assert nimbus.ledgerBorrow(relay.ledgers[0].ledger_address) == 90 * 10**12

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    batch0Token = withdrawal.getXcTokenBalanceForBatch(0)
    assert batch0Token == 495 * 10**11

    assert withdrawal.totalVirtualXcTokenAmount() == 495 * 10**11
    assert withdrawal.totalXcTokenPoolShares() == 55 * 10**12
    assert withdrawal.batchVirtualXcTokenAmount() == 45 * 10**11

    assert available == 0
    assert waiting == 54 * 10**12

    # 5. check available for withdraw balance

    # 6. redeem the rest balance

    assert nimbus.getPooledTokenByShares(nimbus.balanceOf(accounts[0])) == 36 * 10**12

    nimbus.redeem(nimbus.balanceOf(accounts[0]), {'from': accounts[0]})
    relay.new_era()

    batch0Token = withdrawal.getXcTokenBalanceForBatch(0)
    assert batch0Token == 495 * 10**11

    batch1Token = withdrawal.getXcTokenBalanceForBatch(1)
    assert batch1Token == 405 * 10**11

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 90 * 10**12

    relay.timetravel(28) # wait unbonding

    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 495 * 10**11
    assert waiting == 405 * 10**11

    nimbus.claimUnbonded({'from': accounts[0]})
    relay.new_era()
    relay.new_era()
    nimbus.claimUnbonded({'from': accounts[0]})

    assert nimbus.balanceOf(accounts[0]) == 0
    assert withdrawal.totalVirtualXcTokenAmount() == 0
    assert withdrawal.totalXcTokenPoolShares() == 0
    assert xcTOKEN.balanceOf(withdrawal) == 0


def test_redeem_before_losses_second_type(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    # 1. deposit tokens
    deposit = 100 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    relay.new_era()

    assert relay.ledgers[0].active_balance == deposit

    # 1.1 first redeem to make totalXcTokenBalance on Withdrawal > 0
    redeem_1 = 5 * 10**12
    nimbus.redeem(redeem_1, {'from': accounts[0]})

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 5 * 10**12

    relay.new_era()

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 5 * 10**12

    # 2. add new era with loss
    relay.new_era(rewards=[-10 * 10**12], blocked_quorum=[True])

    # 3. redeem tokens before consensus is reached on the ledger
    redeem = 55 * 10**12
    nimbus.redeem(redeem, {'from': accounts[0]})

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 60 * 10**12

    # 4. reach consensus on the ledger
    relay.finalize_quorum(0)

    # 5. check available for withdraw balance

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 54 * 10**12

    # 6. redeem the rest balance
    nimbus.redeem(nimbus.balanceOf(accounts[0]), {'from': accounts[0]})
    relay.new_era()

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 90 * 10**12

    relay.timetravel(28) # wait unbonding

    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal
    relay.new_era() # set batch for second redeem available for claim

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 90 * 10**12
    assert waiting == 0

    nimbus.claimUnbonded({'from': accounts[0]})

    assert nimbus.balanceOf(accounts[0]) == 0
    assert withdrawal.totalXcTokenPoolShares() == 0
    assert withdrawal.totalVirtualXcTokenAmount() == 0
    assert xcTOKEN.balanceOf(withdrawal) == 0


def test_redeem_before_losses_two_ledgers(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    relay.new_ledger("0x20", "0x21")

    # 1. deposit tokens
    deposit = 100 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    relay.new_era()

    assert relay.ledgers[0].active_balance == deposit // 2
    assert relay.ledgers[1].active_balance == deposit // 2

    # 1.1 first redeem to make totalXcTokenBalance on Withdrawal > 0
    redeem_1 = 50 * 10**12
    nimbus.redeem(redeem_1, {'from': accounts[0]})

    relay.new_era()

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 50 * 10**12

    # 2. add new era with loss
    relay.new_era(rewards=[-10 * 10**12, -10 * 10**12], blocked_quorum=[True, True])

    # 3. redeem tokens before consensus is reached on the ledger
    redeem = 10 * 10**12
    nimbus.redeem(redeem, {'from': accounts[0]})

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 60 * 10**12

    # 4. reach consensus on the first ledger
    relay.finalize_quorum(0)

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 54 * 10**12

    # 4.1 reach consensus on the second ledger
    relay.finalize_quorum(1)

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 48 * 10**12

    assert nimbus.ledgerStake(relay.ledgers[0].ledger_address) == 20 * 10**12
    assert nimbus.ledgerStake(relay.ledgers[1].ledger_address) == 20 * 10**12

    assert nimbus.ledgerBorrow(relay.ledgers[0].ledger_address) == 40 * 10**12
    assert nimbus.ledgerBorrow(relay.ledgers[1].ledger_address) == 40 * 10**12

    # 5. check available for withdraw balance

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    batch0Token = withdrawal.getXcTokenBalanceForBatch(0)
    assert batch0Token == 40 * 10**12

    assert available == 0
    assert waiting == 48 * 10**12

    # 6. redeem the rest balance

    assert nimbus.getPooledTokenByShares(nimbus.balanceOf(accounts[0])) == 32 * 10**12

    nimbus.redeem(nimbus.balanceOf(accounts[0]), {'from': accounts[0]})
    relay.new_era()

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 80 * 10**12

    relay.timetravel(28) # wait unbonding

    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    nimbus.claimUnbonded({'from': accounts[0]})
    relay.new_era()
    relay.new_era()
    nimbus.claimUnbonded({'from': accounts[0]})

    assert nimbus.balanceOf(accounts[0]) == 0
    assert withdrawal.totalVirtualXcTokenAmount() == 0
    assert withdrawal.totalXcTokenPoolShares() == 0
    assert xcTOKEN.balanceOf(withdrawal) == 0


def test_redeem_before_losses_fasttracked(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    # 1. deposit tokens
    deposit = 100 * 10**12
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()
    relay.new_era()

    assert relay.ledgers[0].active_balance == deposit

    # 1. first redeem to make totalXcTokenBalance on Withdrawal > 0
    redeem_1 = 55 * 10**12
    nimbus.redeem(redeem_1, {'from': accounts[0]})

    relay.new_era()

    # 1.1 deposit to create fasttracked value > 0
    deposit_2 = 20 * 10**12
    nimbus.deposit(deposit_2, {'from': accounts[0]})

    relay.new_era()

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 55 * 10**12

    # 2. add new era with loss
    relay.new_era(rewards=[-10 * 10**12], blocked_quorum=[True])

    # 3. redeem tokens before consensus is reached on the ledger
    redeem = 5 * 10**12
    nimbus.redeem(redeem, {'from': accounts[0]})

    (waiting, available) = nimbus.getUnbonded(accounts[0])

    assert available == 0
    assert waiting == 60 * 10**12

    # 4. reach consensus on the ledger
    relay.finalize_quorum(0)

    assert nimbus.ledgerStake(relay.ledgers[0].ledger_address) == 585 * 10**11
    assert nimbus.ledgerBorrow(relay.ledgers[0].ledger_address) == 90 * 10**12

    # 5. redeem the rest balance

    nimbus.redeem(nimbus.balanceOf(accounts[0]), {'from': accounts[0]})
    relay.new_era()

    relay.timetravel(28) # wait unbonding

    relay.new_era()  # should send 'withdraw'
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    nimbus.claimUnbonded({'from': accounts[0]})
    relay.new_era()
    relay.new_era()
    nimbus.claimUnbonded({'from': accounts[0]})

    assert nimbus.balanceOf(accounts[0]) == 0
    assert withdrawal.totalVirtualXcTokenAmount() == 0
    assert withdrawal.totalXcTokenPoolShares() == 0
    assert xcTOKEN.balanceOf(withdrawal) < 50