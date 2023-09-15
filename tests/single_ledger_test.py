from brownie import chain
from helpers import RelayChain, distribute_initial_tokens




def test_add_stash(nimbus, oracle_master, xcTOKEN, Ledger, accounts):
    nimbus.addLedger("0x10", "0x20", 0, {'from': accounts[0]})

    ledger = Ledger.at(nimbus.findLedger("0x10"))
    assert ledger.stashAccount() == "0x10"
    assert ledger.controllerAccount() == "0x20"


def test_relay_direct_transfer(nimbus, oracle_master, xcTOKEN, accounts):
    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    relay.new_era()

    assert relay.ledgers[0].free_balance == 0
    assert relay.ledgers[0].active_balance == 0

    reward = 100
    nimbus.setFee(1000, 9000, {'from': accounts[0]})

    relay.new_era([reward])
    assert relay.ledgers[0].active_balance == reward
    assert nimbus.getTotalPooledToken() == reward


def test_losse_underflow(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    # create ledger
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)
    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    # deposit, wait to active balance
    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})
    relay.new_era()
    assert relay.ledgers[0].free_balance == deposit
    assert relay.ledgers[0].active_balance == 0
    relay.new_era()
    assert relay.ledgers[0].free_balance == 0
    assert relay.ledgers[0].active_balance == deposit

    # transfer directly to ledger
    direct_transfer = 10**18
    xcTOKEN.transfer(relay.ledgers[0].ledger_address, direct_transfer, {'from': accounts[0]})
    relay.new_era()

    # withdraw one part
    first_redeem = 10 * 10**18
    nimbus.redeem(first_redeem, {'from': accounts[0]})
    relay.new_era()

    # wait unbonding period
    for i in range(32):
        relay.new_era()

    nimbus.setMaxAllowableDifference(100000000, {'from': accounts[0]})

    # make sure that some tokens locked on Withdrawal
    assert xcTOKEN.balanceOf(withdrawal) == first_redeem
    nimbus.claimUnbonded({'from': accounts[0]})
    assert xcTOKEN.balanceOf(withdrawal) == 0 # NOTE: excess is still on withdrawal

    # distribute losses
    relay.new_era([-first_redeem])


def test_direct_ledger_transfer(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    # create ledger
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)
    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    # deposit, wait to active balance
    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})
    relay.new_era()
    assert relay.ledgers[0].free_balance == deposit
    assert relay.ledgers[0].active_balance == 0
    relay.new_era()
    assert relay.ledgers[0].free_balance == 0
    assert relay.ledgers[0].active_balance == deposit

    # transfer directly to ledger
    direct_transfer = 10**18
    xcTOKEN.transfer(relay.ledgers[0].ledger_address, direct_transfer, {'from': accounts[0]})
    relay.new_era()

    # withdraw one part
    first_redeem = 10 * 10**18
    nimbus.redeem(first_redeem, {'from': accounts[0]})
    relay.new_era()

    # wait unbonding period
    for i in range(32):
        relay.new_era()

    # make sure that some tokens locked on Withdrawal
    assert xcTOKEN.balanceOf(withdrawal) == first_redeem
    nimbus.claimUnbonded({'from': accounts[0]})
    assert xcTOKEN.balanceOf(withdrawal) == 0 # NOTE: excess goes as rewards to nimbus

    # redeem all
    second_redeem = 10 * 10**18 # the user has `initial shares - first redeem`, but now shares price increases because of direct transfer
    nimbus.redeem(second_redeem, {'from': accounts[0]})
    relay.new_era()

    # wait unbonding period
    for i in range(32):
        relay.new_era()

    # check how it work with excess
    assert xcTOKEN.balanceOf(withdrawal) == second_redeem + direct_transfer
    nimbus.claimUnbonded({'from': accounts[0]})
    assert xcTOKEN.balanceOf(withdrawal) == 0
    assert nimbus.fundRaisedBalance() == 0


def test_nominate_batch_ledger(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    relay.new_ledger("0x20", "0x21")
    relay.new_ledger("0x30", "0x31")

    deposit = 30 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()

    assert relay.ledgers[0].free_balance == deposit // 3
    assert relay.ledgers[0].active_balance == 0

    relay.new_era()

    assert relay.ledgers[0].free_balance == 0
    assert relay.ledgers[0].active_balance == deposit // 3

    relay.new_era()

    nimbus.nominateBatch([relay.ledgers[0].stash_account, relay.ledgers[1].stash_account, relay.ledgers[2].stash_account], [['0x123', '0x333', '0x131'], ['0x213'], ['0x321']])


def test_deposit_bond_disable(nimbus, Ledger, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    relay.disable_bond()

    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()

    ledger = Ledger.at(relay.ledgers[0].ledger_address)
    assert ledger.pendingBonds() == 0

    assert relay.ledgers[0].free_balance == deposit
    assert relay.ledgers[0].active_balance == 0

    deposit2 = 30 * 10**18
    nimbus.deposit(deposit2, {'from': accounts[0]})

    relay.new_era()
    assert ledger.pendingBonds() == 20 * 10**18

    assert relay.ledgers[0].active_balance == 0
    assert relay.ledgers[0].free_balance == deposit + deposit2
    assert nimbus.getTotalPooledToken() == deposit + deposit2

    relay.new_era()
    assert ledger.pendingBonds() == 50 * 10**18

    relay.new_era()
    assert ledger.pendingBonds() == 50 * 10**18

    deposit3 = 5 * 10**18
    nimbus.deposit(deposit3, {'from': accounts[0]})

    relay.new_era()
    assert ledger.pendingBonds() == 50 * 10**18

    assert relay.ledgers[0].active_balance == 0
    assert relay.ledgers[0].free_balance == deposit + deposit2 + deposit3
    assert nimbus.getTotalPooledToken() == deposit + deposit2 + deposit3


def test_deposit_bond_disable_enable(nimbus, Ledger, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    relay.disable_bond()

    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()

    ledger = Ledger.at(relay.ledgers[0].ledger_address)
    assert ledger.pendingBonds() == 0

    assert relay.ledgers[0].free_balance == deposit
    assert relay.ledgers[0].active_balance == 0

    deposit2 = 30 * 10**18
    nimbus.deposit(deposit2, {'from': accounts[0]})

    relay.new_era()
    assert ledger.pendingBonds() == 20 * 10**18

    assert relay.ledgers[0].active_balance == 0
    assert relay.ledgers[0].free_balance == deposit + deposit2
    assert nimbus.getTotalPooledToken() == deposit + deposit2

    relay.new_era()
    assert ledger.pendingBonds() == 50 * 10**18

    relay.new_era()
    assert ledger.pendingBonds() == 50 * 10**18

    relay.enable_bond()

    relay.new_era()
    assert relay.ledgers[0].active_balance == deposit + deposit2
    assert relay.ledgers[0].free_balance == 0
    assert ledger.pendingBonds() == 50 * 10**18

    relay.disable_transfer()
    relay.new_era()
    assert ledger.pendingBonds() == 0

    deposit3 = 5 * 10**18
    nimbus.deposit(deposit3, {'from': accounts[0]})

    relay.new_era()
    assert ledger.pendingBonds() == 0

    assert relay.ledgers[0].active_balance == deposit + deposit2
    assert relay.ledgers[0].free_balance == 0
    assert nimbus.getTotalPooledToken() == deposit + deposit2 + deposit3

    relay.new_era()
    assert ledger.pendingBonds() == 0
    assert nimbus.getTotalPooledToken() == deposit + deposit2 + deposit3


def test_equal_deposit_bond(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()

    assert relay.ledgers[0].free_balance == deposit
    assert relay.ledgers[0].active_balance == 0

    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()

    assert relay.ledgers[0].active_balance == deposit - 1
    assert relay.ledgers[0].free_balance == deposit + 1
    assert nimbus.getTotalPooledToken() == 2 * deposit

    deposit3 = 5 * 10**18
    nimbus.deposit(deposit3, {'from': accounts[0]})

    relay.new_era()
    assert relay.ledgers[0].active_balance == 2 * deposit
    assert relay.ledgers[0].free_balance == deposit3
    assert nimbus.getTotalPooledToken() == 2 * deposit + deposit3

def test_deposit_transfer_disable(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    relay.disable_transfer()

    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()

    assert relay.ledgers[0].free_balance == 0
    assert relay.ledgers[0].active_balance == 0

    deposit2 = 30 * 10**18
    nimbus.deposit(deposit2, {'from': accounts[0]})

    relay.new_era()

    assert relay.ledgers[0].active_balance == 0
    assert relay.ledgers[0].free_balance == 0
    assert nimbus.getTotalPooledToken() == deposit + deposit2

def test_double_deposit(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()

    assert relay.ledgers[0].free_balance == deposit
    assert relay.ledgers[0].active_balance == 0

    deposit2 = 30 * 10**18
    nimbus.deposit(deposit2, {'from': accounts[0]})

    relay.new_era()

    assert relay.ledgers[0].active_balance == deposit
    assert relay.ledgers[0].free_balance == deposit2
    assert nimbus.getTotalPooledToken() == deposit + deposit2

    deposit3 = 5 * 10**18
    nimbus.deposit(deposit3, {'from': accounts[0]})

    relay.new_era()
    assert relay.ledgers[0].active_balance == deposit + deposit2
    assert relay.ledgers[0].free_balance == deposit3
    assert nimbus.getTotalPooledToken() == deposit + deposit2 + deposit3

def test_deposit_with_direct_transfer(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()

    assert relay.ledgers[0].free_balance == deposit
    assert relay.ledgers[0].active_balance == 0

    deposit2 = 30 * 10**18
    nimbus.deposit(deposit2, {'from': accounts[0]})
    direct_transfer = 1 * 10**18
    relay.ledgers[0].free_balance += direct_transfer # direct transfer

    relay.new_era()

    assert relay.ledgers[0].active_balance == deposit + direct_transfer
    assert relay.ledgers[0].free_balance == deposit2
    assert nimbus.getTotalPooledToken() == deposit + deposit2 + direct_transfer # direct transfer work as rewards

    deposit3 = 5 * 10**18
    nimbus.deposit(deposit3, {'from': accounts[0]})

    relay.new_era()
    assert relay.ledgers[0].active_balance == deposit + deposit2 + direct_transfer
    assert relay.ledgers[0].free_balance == deposit3
    assert nimbus.getTotalPooledToken() == deposit + deposit2 + deposit3 + direct_transfer # direct transfer work as rewards

def test_single_deposit(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()

    assert relay.ledgers[0].free_balance == deposit
    assert relay.ledgers[0].active_balance == 0

    reward = 123
    relay.new_era([reward])
    assert relay.ledgers[0].active_balance == deposit + reward
    assert nimbus.getTotalPooledToken() == deposit + reward


def test_multi_deposit(nimbus, oracle_master, xcTOKEN, accounts, developers, treasury):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit1 = 20 * 10**18
    deposit2 = 5 * 10**18
    deposit3 = 100 * 10**18
    nimbus.deposit(deposit1, {'from': accounts[0]})
    nimbus.deposit(deposit2, {'from': accounts[1]})
    nimbus.deposit(deposit3, {'from': accounts[2]})

    relay.new_era()

    assert relay.ledgers[0].free_balance == deposit1 + deposit2 + deposit3
    assert relay.ledgers[0].active_balance == 0

    reward = 3 * 10**18
    relay.new_era([reward])
    assert relay.ledgers[0].active_balance == deposit1 + deposit2 + deposit3 + reward
    assert nimbus.getTotalPooledToken() == deposit1 + deposit2 + deposit3 + reward

    acc1_balance = nimbus.balanceOf(accounts[0])
    assert acc1_balance == deposit1

    acc2_balance = nimbus.balanceOf(accounts[1])
    assert acc2_balance == deposit2

    acc3_balance = nimbus.balanceOf(accounts[2])
    assert acc3_balance == deposit3

    nimbus_rewards = nimbus.balanceOf(nimbus)
    assert nimbus_rewards == 0

    developers_rewards = nimbus.balanceOf(developers)
    assert developers_rewards == 58731401722787783 # ~2% of rewards in xcToken

    treasury_rewards = nimbus.balanceOf(treasury)
    assert treasury_rewards == 234925606891151136 # ~8% of rewards in xcToken

    assert nimbus.getTotalPooledToken() == deposit1 + deposit2 + deposit3 + reward

    assert abs(
        nimbus.getPooledTokenByShares(acc1_balance) + nimbus.getPooledTokenByShares(acc2_balance) + 
        nimbus.getPooledTokenByShares(acc3_balance) + nimbus.getPooledTokenByShares(nimbus_rewards) + 
        nimbus.getPooledTokenByShares(developers_rewards) + nimbus.getPooledTokenByShares(treasury_rewards) -
        nimbus.getTotalPooledToken()
    ) <= 1000


def test_redeem(nimbus, oracle_master, xcTOKEN, withdrawal, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit1 = 20 * 10**18
    deposit2 = 5 * 10**18
    deposit3 = 100 * 10**18
    nimbus.deposit(deposit1, {'from': accounts[0]})
    nimbus.deposit(deposit2, {'from': accounts[1]})
    nimbus.deposit(deposit3, {'from': accounts[2]})

    relay.new_era()

    reward = 3 * 10**18
    relay.new_era([reward])
    assert relay.ledgers[0].active_balance == deposit1 + deposit2 + deposit3 + reward
    assert nimbus.getTotalPooledToken() == deposit1 + deposit2 + deposit3 + reward

    balance_for_redeem = nimbus.balanceOf(accounts[1])

    nimbus.redeem(balance_for_redeem, {'from': accounts[1]})

    withdrawal_balance_start = withdrawal.batchVirtualXcTokenAmount()
    assert withdrawal_balance_start == nimbus.getPooledTokenByShares(balance_for_redeem) # NOTE: withdrawal works with xcToken balance

    relay.new_era([reward])

    withdrawal_balance = withdrawal.batchVirtualXcTokenAmount()
    withdrawal_total_balance = withdrawal.totalVirtualXcTokenAmount()
    assert withdrawal_balance == 0
    assert withdrawal_total_balance == withdrawal_balance_start

    # travel for 29 eras
    relay.timetravel(29)

    relay.new_era([reward])  # should send 'withdraw'
    relay.new_era([reward])  # should downward transfer
    relay.new_era([reward])  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    withdrawal_xc_token = xcTOKEN.balanceOf(withdrawal)
    assert withdrawal_xc_token == withdrawal_balance_start

    claimable_id = withdrawal.claimableId()
    assert claimable_id == 1

    balance_before_claim = xcTOKEN.balanceOf(accounts[1])
    nimbus.claimUnbonded({'from': accounts[1]})

    assert xcTOKEN.balanceOf(accounts[1]) == withdrawal_balance_start + balance_before_claim
    assert nimbus.getTotalPooledToken() == deposit1 + deposit2 + deposit3 + 5*reward - withdrawal_balance_start


def test_multi_redeem(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[1]})

    relay.new_era()

    assert relay.ledgers[0].free_balance == deposit
    assert relay.ledgers[0].active_balance == 0

    reward = 123
    relay.new_era([reward])
    assert relay.ledgers[0].active_balance == deposit + reward
    assert nimbus.getTotalPooledToken() == deposit + reward

    redeem_1 = 5 * 10**18
    redeem_2 = 6 * 10**18
    redeem_3 = 7 * 10**18

    redeem_1_xcToken = nimbus.getPooledTokenByShares(redeem_1)
    nimbus.redeem(redeem_1, {'from': accounts[1]})
    relay.new_era([reward])

    assert nimbus.getUnbonded(accounts[1]) == (redeem_1_xcToken, 0)

    redeem_2_xcToken = nimbus.getPooledTokenByShares(redeem_2)
    nimbus.redeem(redeem_2, {'from': accounts[1]})
    relay.new_era([reward])

    assert nimbus.getUnbonded(accounts[1]) == (redeem_1_xcToken + redeem_2_xcToken, 0)

    redeem_3_xcToken = nimbus.getPooledTokenByShares(redeem_3)
    nimbus.redeem(redeem_3, {'from': accounts[1]})
    relay.new_era([reward])

    assert nimbus.getUnbonded(accounts[1]) == (redeem_1_xcToken + redeem_2_xcToken + redeem_3_xcToken, 0)

    # travel for 26 eras
    relay.timetravel(26) 

    # eras for transfer tokens to withdrawal
    relay.new_era() # withdraw
    relay.new_era() # transfer to relay chain
    relay.new_era() # transfer to withdrawal
    relay.new_era() # update era in withdrawal

    assert nimbus.getUnbonded(accounts[1]) == (redeem_3_xcToken + redeem_2_xcToken, redeem_1_xcToken)

    relay.new_era()
    assert nimbus.getUnbonded(accounts[1]) == (redeem_3_xcToken, redeem_2_xcToken + redeem_1_xcToken)

    relay.new_era()
    assert nimbus.getUnbonded(accounts[1]) == (0, redeem_3_xcToken + redeem_2_xcToken + redeem_1_xcToken)

    relay.new_era([reward])
    relay.new_era([reward])  # should send 'withdraw'
    relay.new_era([reward])  # should downward transfer
    relay.new_era([reward])  # should downward transfer got completed

    balance_before_claim = xcTOKEN.balanceOf(accounts[1])
    nimbus.claimUnbonded({'from': accounts[1]})

    assert xcTOKEN.balanceOf(accounts[1]) == redeem_3_xcToken + redeem_2_xcToken + redeem_1_xcToken + balance_before_claim


def test_multi_redeem_order_removal(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[1]})

    relay.new_era()

    assert relay.ledgers[0].free_balance == deposit
    assert relay.ledgers[0].active_balance == 0

    reward = 123
    relay.new_era([reward])
    assert relay.ledgers[0].active_balance == deposit + reward
    assert nimbus.getTotalPooledToken() == deposit + reward

    redeem_1 = 5 * 10**18
    redeem_2 = 6 * 10**18
    redeem_3 = 7 * 10**18

    redeem_1_xcToken = nimbus.getPooledTokenByShares(redeem_1)
    nimbus.redeem(redeem_1, {'from': accounts[1]})
    relay.new_era([reward])
    relay.timetravel(7)

    assert nimbus.getUnbonded(accounts[1]) == (redeem_1_xcToken, 0)

    redeem_2_xcToken = nimbus.getPooledTokenByShares(redeem_2)
    nimbus.redeem(redeem_2, {'from': accounts[1]})
    relay.new_era([reward])
    relay.timetravel(7)

    assert nimbus.getUnbonded(accounts[1]) == (redeem_1_xcToken + redeem_2_xcToken, 0)

    redeem_3_xcToken = nimbus.getPooledTokenByShares(redeem_3)
    nimbus.redeem(redeem_3, {'from': accounts[1]})
    relay.new_era([reward])
    relay.timetravel(7)

    assert nimbus.getUnbonded(accounts[1]) == (redeem_1_xcToken + redeem_2_xcToken + redeem_3_xcToken, 0)

    relay.timetravel(5)
    relay.new_era() # withdraw
    relay.new_era() # transfer to relay chain
    relay.new_era() # transfer to withdrawal
    relay.new_era() # update era in withdrawal

    assert nimbus.getUnbonded(accounts[1]) == (redeem_2_xcToken + redeem_3_xcToken, redeem_1_xcToken)

    relay.new_era([reward])
    relay.new_era([reward])  # should send 'withdraw'
    relay.new_era([reward])  # should downward transfer
    relay.new_era([reward])  # should downward transfer got completed

    balance_before_claim = xcTOKEN.balanceOf(accounts[1])
    nimbus.claimUnbonded({'from': accounts[1]})

    assert xcTOKEN.balanceOf(accounts[1]) == redeem_1_xcToken + balance_before_claim
    assert nimbus.getUnbonded(accounts[1]) == (redeem_2_xcToken + redeem_3_xcToken, 0)


def test_is_reported_indicator(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})

    assert oracle_master.isReportedLastEra(accounts[0], relay.ledgers[0].stash_account) == (0, False)

    relay.new_era()
    assert oracle_master.isReportedLastEra(accounts[0], relay.ledgers[0].stash_account) == (relay.era, True)


def test_soften_quorum(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")
    ledger_1 = relay.ledgers[0]

    oracle_master.setQuorum(3, {'from': accounts[0]})

    deposit = 20 * 10**18
    nimbus.deposit(deposit, {'from': accounts[0]})

    relay.new_era()

    assert ledger_1.free_balance == 0

    tx = oracle_master.setQuorum(2, {'from': accounts[0]})

    relay._after_report(tx)

    assert ledger_1.free_balance == deposit

    oracle_master.addOracleMember(accounts[2], {'from': accounts[0]})
    oracle_master.removeOracleMember(accounts[2], {'from': accounts[0]})