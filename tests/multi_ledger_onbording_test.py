from brownie import chain, Ledger
from helpers import RelayChain, distribute_initial_tokens


def check_distribution(nimbus, stashes, total_deposit):
    stakes_sum =0
    for i in range(len(stashes)):
        stash = hex(stashes[i])
        ledger = Ledger.at(nimbus.findLedger(stash))
        stakes_sum += ledger.ledgerStake()
        target = total_deposit // len(stashes)
        assert abs(ledger.ledgerStake() - target) / target < 0.01
    assert stakes_sum == total_deposit


def test_add_ledger_slowly(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)
    stashes = [0x10]
    total_deposit = 0

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger(hex(stashes[0]), hex(stashes[0]+1))

    deposit = 1000 * 10**18
    total_deposit += deposit
    nimbus.deposit(deposit, {'from': accounts[0]})

    rewards = 3 * 10**18
    relay.new_era([rewards])
    relay.new_era([rewards])
    check_distribution(nimbus, stashes, total_deposit + relay.total_rewards)

    assert relay.ledgers[0].active_balance == relay.total_rewards + total_deposit

    # new stash
    stashes.append(0x20)
    relay.new_ledger(hex(stashes[1]), hex(stashes[1]+1))

    total_deposit += deposit
    nimbus.deposit(deposit, {'from': accounts[0]})
    relay.new_era()  # send unbond for first ledger
    # check target stake distribution
    check_distribution(nimbus, stashes, total_deposit + relay.total_rewards)
    relay.timetravel(29)  # wait for unbonding period
    relay.new_era()  # send withdraw for first ledger
    relay.new_era()  # downward transfer from first ledger
    relay.new_era()  # upward transfer for second ledger
    relay.new_era()  # bond for first ledger

    assert relay.ledgers[0].active_balance == Ledger.at(nimbus.findLedger(hex(stashes[0]))).ledgerStake()
    assert relay.ledgers[1].active_balance == Ledger.at(nimbus.findLedger(hex(stashes[1]))).ledgerStake()


def test_remove_ledger_slowly(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)
    stashes = [0x10, 0x20]
    total_deposit = 0

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger(hex(stashes[0]), hex(stashes[0]+1))
    relay.new_ledger(hex(stashes[1]), hex(stashes[1]+1))

    deposit = 1000 * 10**18
    total_deposit += deposit
    nimbus.deposit(deposit, {'from': accounts[0]})

    rewards = 3 * 10**18
    relay.new_era([rewards, rewards])  # upward transfer
    relay.new_era([rewards, rewards])  # bond
    total_deposit += deposit
    nimbus.deposit(deposit, {'from': accounts[0]})
    relay.new_era()

    check_distribution(nimbus, stashes, total_deposit + relay.total_rewards)

    # disable ledger
    nimbus.disableLedger(relay.ledgers[1].ledger_address, {'from': accounts[0]})

    nimbus.redeem(nimbus.getSharesByPooledToken(deposit + 2 * rewards), {'from': accounts[0]})
    total_deposit -= deposit + 2*rewards
    relay.new_era()  # send unbond for second ledger

    # check target stake distribution
    check_distribution(nimbus, stashes[:1], total_deposit + relay.total_rewards)

    relay.timetravel(29)  # wait for unbonding period

    relay.new_era([rewards])  # send withdraw for second ledger

    relay.new_era([rewards])  # downward transfer from second ledger
    relay.new_era([rewards])  # upward transfer for first ledger
    relay.new_era([rewards])  # bondextra for fisrt ledger
    relay.new_era([rewards])  # bondextra for fisrt ledger [it depend on oracle_masterReport order accross ledgers]

    assert relay.ledgers[1].status == 'Chill'

    assert relay.ledgers[0].active_balance == Ledger.at(nimbus.findLedger(hex(stashes[0]))).ledgerStake()
    assert relay.ledgers[1].active_balance == Ledger.at(nimbus.findLedger(hex(stashes[1]))).ledgerStake()
    assert relay.ledgers[1].active_balance == 0
    assert relay.total_rewards + total_deposit == nimbus.getTotalPooledToken()


def test_redeems_to_disabled_ledger(nimbus, oracle_master, xcTOKEN, accounts):
    distribute_initial_tokens(xcTOKEN, nimbus, accounts)
    stashes = [0x10, 0x20]
    total_deposit = 0

    relay = RelayChain(nimbus, xcTOKEN, oracle_master, accounts, chain)
    relay.new_ledger(hex(stashes[0]), hex(stashes[0]+1))
    relay.new_ledger(hex(stashes[1]), hex(stashes[1]+1))

    led1 = relay.ledgers[0].ledger_address
    led2 = relay.ledgers[1].ledger_address

    rewards = 3 * 10**18
    deposit_1 = 1000 * 10**18
    nimbus.deposit(deposit_1, {'from': accounts[0]})
    relay.new_era([rewards, rewards])

    assert nimbus.ledgerStake(led1) == deposit_1 // 2 + rewards
    assert nimbus.ledgerStake(led2) == deposit_1 // 2 + rewards

    # disable ledger
    nimbus.disableLedger(relay.ledgers[1].ledger_address, {'from': accounts[0]})

    deposit_2 = 100 * 10**18
    redeem_1 = 200 * 10**18
    nimbus.deposit(deposit_2, {'from': accounts[0]})
    nimbus.redeem(nimbus.getSharesByPooledToken(redeem_1), {'from': accounts[0]})
    relay.new_era([rewards, rewards])

    assert nimbus.ledgerStake(led1) == deposit_1 // 2 + deposit_2 + 2 * rewards
    assert nimbus.ledgerStake(led2) == deposit_1 // 2 - redeem_1 + 2 * rewards + 1 # NOTE: +1 because of the rounding

    redeem_2 = deposit_1 // 2 - redeem_1 + 2 * rewards
    nimbus.redeem(nimbus.getSharesByPooledToken(redeem_2 + 2), {'from': accounts[0]})
    relay.new_era([rewards, 0])

    assert nimbus.ledgerStake(led1) == deposit_1 // 2 + deposit_2 + 3 * rewards
    assert nimbus.ledgerStake(led2) == 0

    relay.timetravel(29)  # wait for unbonding period

    relay.new_era()  # send withdraw for second ledger
    relay.new_era()  # downward transfer from second ledger

    assert relay.ledgers[1].status == 'Chill'

    assert relay.ledgers[0].active_balance == Ledger.at(nimbus.findLedger(hex(stashes[0]))).ledgerStake()
    assert relay.ledgers[1].active_balance == Ledger.at(nimbus.findLedger(hex(stashes[1]))).ledgerStake()
    assert relay.ledgers[1].active_balance == 0
    assert relay.total_rewards + deposit_1 + deposit_2 - redeem_1 - redeem_2 == nimbus.getTotalPooledToken()
