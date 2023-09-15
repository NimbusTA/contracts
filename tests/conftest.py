import pytest
from pathlib import Path
from brownie import project, config

# import oz project
project.load(Path.home() / ".brownie" / "packages" / config["dependencies"][0])
if hasattr(project, 'OpenzeppelinContracts410Project'):
    OpenzeppelinContractsProject = project.OpenzeppelinContracts410Project
else:
    OpenzeppelinContractsProject = project.OpenzeppelinContractsProject


def deploy_with_proxy(contract, proxy_admin, *args):
    TransparentUpgradeableProxy = OpenzeppelinContractsProject.TransparentUpgradeableProxy
    owner = proxy_admin.owner()
    logic_instance = contract.deploy({'from': owner})
    encoded_inputs = logic_instance.initialize.encode_input(*args)

    proxy_instance = TransparentUpgradeableProxy.deploy(
        logic_instance,
        proxy_admin,
        encoded_inputs,
        {'from': owner, 'gas_limit': 10**6}
    )

    TransparentUpgradeableProxy.remove(proxy_instance)
    return (contract.at(proxy_instance.address, owner=owner), logic_instance)


@pytest.fixture(scope="function", autouse=True)
def isolate(fn_isolation):
    pass


@pytest.fixture(scope="module")
def proxy_admin(accounts):
    ProxyAdmin = OpenzeppelinContractsProject.ProxyAdmin
    return ProxyAdmin.deploy({'from': accounts[0]})


@pytest.fixture(scope="module")
def xcTOKEN(xcTOKEN_mock, accounts):
    return xcTOKEN_mock.deploy({'from': accounts[0]})


@pytest.fixture(scope="module")
def auth_manager(AuthManager, proxy_admin, accounts):
    (am, _) = deploy_with_proxy(AuthManager, proxy_admin, accounts[0])
    am.addByString('ROLE_SPEC_MANAGER', accounts[0], {'from': accounts[0]})
    am.addByString('ROLE_BEACON_MANAGER', accounts[0], {'from': accounts[0]})
    am.addByString('ROLE_PAUSE_MANAGER', accounts[0], {'from': accounts[0]})
    am.addByString('ROLE_FEE_MANAGER', accounts[0], {'from': accounts[0]})
    am.addByString('ROLE_LEDGER_MANAGER', accounts[0], {'from': accounts[0]})
    am.addByString('ROLE_STAKE_MANAGER', accounts[0], {'from': accounts[0]})
    am.addByString('ROLE_ORACLE_MEMBERS_MANAGER', accounts[0], {'from': accounts[0]})
    am.addByString('ROLE_ORACLE_QUORUM_MANAGER', accounts[0], {'from': accounts[0]})

    am.addByString('ROLE_SET_TREASURY', accounts[0], {'from': accounts[0]})
    am.addByString('ROLE_SET_DEVELOPERS', accounts[0], {'from': accounts[0]})
    return am


@pytest.fixture(scope="module")
def oracle_master(Oracle, OracleMaster, Ledger, accounts, chain):
    o = Oracle.deploy({'from': accounts[0]})
    om = OracleMaster.deploy({'from': accounts[0]})
    om.initialize(o, 1, {'from': accounts[0]})
    return om


@pytest.fixture(scope="module")
def withdrawal(Withdrawal, xcTOKEN, accounts):
    wdr = Withdrawal.deploy({'from': accounts[0]})
    wdr.initialize(35, xcTOKEN, {'from': accounts[0]})
    return wdr


@pytest.fixture(scope="module")
def controller(Controller_mock, accounts, chain):
    c = Controller_mock.deploy({'from': accounts[0]})
    return c


@pytest.fixture(scope="module")
def admin(accounts):
    return accounts[0]


@pytest.fixture(scope="module")
def treasury(accounts):
    return accounts.add()


@pytest.fixture(scope="module")
def developers(accounts):
    return accounts.add()


@pytest.fixture(scope="module")
def nimbus(Nimbus, xcTOKEN, controller, auth_manager, oracle_master, withdrawal, proxy_admin, chain, Ledger, LedgerBeacon, LedgerFactory, accounts, developers, treasury):
    lc = Ledger.deploy({'from': accounts[0]})
    (_nimbus, _nimbus_impl) = deploy_with_proxy(Nimbus, proxy_admin, auth_manager, xcTOKEN, controller, developers, treasury, oracle_master, withdrawal, 50000 * 10**18, 3000, "TST", "TST", 12)
    ledger_beacon = LedgerBeacon.deploy(lc, _nimbus, {'from': accounts[0]})
    ledger_factory = LedgerFactory.deploy(_nimbus, ledger_beacon, {'from': accounts[0]})
    _nimbus.setLedgerBeacon(ledger_beacon)
    _nimbus.setLedgerFactory(ledger_factory)

    era_sec = 60 * 60 * 6
    _nimbus.setRelaySpec((16, 1, 0, 32))  # kusama settings except min nominator bond
    oracle_master.setAnchorEra(0, chain.time(), era_sec)
    return _nimbus


@pytest.fixture(scope="module")
def mocknimbus(Nimbus, LedgerMock, LedgerBeacon, LedgerFactory, Oracle, OracleMaster, Withdrawal, xcTOKEN, controller, auth_manager, admin, developers, treasury):
    lc = LedgerMock.deploy({'from': admin})
    o = Oracle.deploy({'from': admin})
    om = OracleMaster.deploy({'from': admin})
    om.initialize(o, 1, {'from': admin})
    wdr = Withdrawal.deploy({'from': admin})
    wdr.initialize(35, xcTOKEN, {'from': admin})

    _nimbus = Nimbus.deploy({'from': admin})
    _nimbus.initialize(auth_manager, xcTOKEN, controller, developers, treasury, om, wdr, 50000 * 10**18, 3000, "TST", "TST", 12, {'from': admin})
    ledger_beacon = LedgerBeacon.deploy(lc, _nimbus, {'from': admin})
    ledger_factory = LedgerFactory.deploy(_nimbus, ledger_beacon, {'from': admin})
    _nimbus.setLedgerBeacon(ledger_beacon, {'from': admin})
    _nimbus.setLedgerFactory(ledger_factory, {'from': admin})

    return _nimbus


@pytest.fixture(scope="module")
def mockledger(mocknimbus, admin, LedgerMock):
    mocknimbus.addLedger(0x01, 0x01, 0, {'from': admin})
    return LedgerMock.at(mocknimbus.findLedger(0x01))
