from brownie import chain
from helpers import RelayChain, distribute_initial_tokens



def test_reward_frontrunning(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger("0x10", "0x11")

    deposit1 = 20 * 10**18
    nimbus.deposit(deposit1, {'from': accounts[0]})

    relay.new_era()
    assert relay.ledgers[0].free_balance == deposit1
    assert relay.ledgers[0].active_balance == 0

    deposit2 = 5 * 10**18
    # Deposit right before report with reward for ledger
    nimbus.deposit(deposit2, {'from': accounts[1]})
    acc2_balance_before = nimbus.balanceOf(accounts[1])

    print('NIMBUS balance of user before: ' + str(acc2_balance_before / 10**18))

    reward = 3 * 10**18
    relay.new_era([reward])
    assert relay.ledgers[0].active_balance == deposit1 + reward
    assert nimbus.getTotalPooledToken() == deposit1 + deposit2 + reward

    acc1_balance = nimbus.balanceOf(accounts[0])
    acc2_balance = nimbus.balanceOf(accounts[1])
    print('NIMBUS balance of user after: ' + str(acc2_balance / 10**18))
    print('user profit: ' + str((acc2_balance - acc2_balance_before) / 10**18))

    # redeem rewards (but if somebody add nTOKEN/xcTOKEN pool in moonbeam MEV can use fl to increase profit)
    balance_for_redeem = nimbus.balanceOf(accounts[1])
    nimbus.redeem(balance_for_redeem, {'from': accounts[1]})

    balance_before_claim = xcTOKEN.balanceOf(accounts[1])

    relay.new_era()

    # move time forward to 28 epoches
    relay.timetravel(28)

    relay.new_era()  # should send 'withdraw'acc1_balance
    relay.new_era()  # should downward transfer
    relay.new_era()  # should downward transfer got completed
    relay.new_era()  # update era in withdrawal

    # Deposit to add some funds to redeem
    deposit3 = 10 * 10**18
    nimbus.deposit(deposit3, {'from': accounts[2]})

    nimbus.claimUnbonded({'from': accounts[1]})
    profit = acc2_balance - acc2_balance_before

    assert xcTOKEN.balanceOf(accounts[1]) == balance_for_redeem + balance_before_claim
    assert profit > 0