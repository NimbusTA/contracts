from brownie import reverts

MUNIT =     1_000_000
UNIT  = 1_000_000_000


def test_fee_distribution(xcTOKEN, mocknimbus, mockledger, treasury, developers, admin):
    '''
    Use default fee distribution:
    total 10% fee splits between treasury 8%  and developers 2%
    '''
    assert mocknimbus.balanceOf(admin) == 0
    xcTOKEN.approve(mocknimbus, 10*UNIT, {'from': admin})
    mocknimbus.deposit(10 * UNIT, {'from': admin})

    initial_token_price = mocknimbus.getPooledTokenByShares(10 * UNIT)

    assert mocknimbus.balanceOf(admin) == 10 * UNIT

    assert mocknimbus.balanceOf(treasury) == 0
    assert mocknimbus.balanceOf(developers) == 0

    # call nimbus.distributeRewards via mock Ledger
    t = mockledger.distributeRewards(1*UNIT, 0, {'from': admin})

    end_token_price = mocknimbus.getPooledTokenByShares(10 * UNIT)

    assert end_token_price > initial_token_price # token price increases

    balance = mocknimbus.balanceOf(admin)
    assert balance == 10_000_000_000  # balance remains the same, token price increases
    balance = mocknimbus.balanceOf(treasury)
    assert balance == 73_394_496  # ~80 MUNIT in xcToken (fee 8%)
    balance = mocknimbus.balanceOf(developers)
    assert balance == 18_348_623   # ~20 MUNIT in xcToken (fee 2%)
    balance = mocknimbus.balanceOf(mocknimbus)
    assert balance == 0  # remains unchanged


def test_fee_change_distribution(xcTOKEN, mocknimbus, mockledger, treasury, developers, admin):
    xcTOKEN.approve(mocknimbus, 10 * UNIT, {'from': admin})
    mocknimbus.deposit(10 * UNIT, {'from': admin})

    assert mocknimbus.balanceOf(admin) == 10 * UNIT
    # call nimbus.distributeRewards via mock Ledger
    mocknimbus.setFee(0, 700)

    assert mocknimbus.balanceOf(treasury) == 0
    t = mockledger.distributeRewards(1*UNIT, 0, {'from': admin})

    assert mocknimbus.balanceOf(treasury) == 0
    assert mocknimbus.balanceOf(developers) == 64_043_915  # ~70 MUNIT in xcToken
    assert mocknimbus.getPooledTokenByShares(mocknimbus.balanceOf(developers)) == 69_999_999

    mocknimbus.setFee(300, 700)
    # call nimbus.distributeRewards via mock Ledger
    mockledger.distributeRewards(1*UNIT, 0, {'from': admin})

    assert mocknimbus.balanceOf(treasury) == 25_371_540    # ~30 MUNIT in xcToken
    assert mocknimbus.getPooledTokenByShares(mocknimbus.balanceOf(treasury)) == 30_000_000

    assert mocknimbus.balanceOf(developers) == 123_244_172 # ~ 70 + 70 MUNIT in xcToken
    assert mocknimbus.getPooledTokenByShares(mocknimbus.balanceOf(developers)) == 145_727_270

    with reverts("NIMBUS: FEE_DONT_ADD_UP"):
        mocknimbus.setFee(0, 0)

    with reverts("NIMBUS: FEE_DONT_ADD_UP"):
        mocknimbus.setFee(5000, 6000)


def test_change_cap(nimbus, accounts):
    cap = 100 * 10**12
    nimbus.setDepositCap(100 * 10**12, {'from': accounts[0]})
    assert nimbus.depositCap() == cap
