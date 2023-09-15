from substrateinterface import Keypair
from substrateinterface import SubstrateInterface
from pathlib import Path
from brownie import *
import base58
from hashlib import blake2b
import json
import yaml
from pathlib import Path
from colorama import Fore, Back, Style, init
import os

init(autoreset=True)


NETWORK=os.getenv("NETWORK", "polkadot")


def get_derivative_account(root_account, index):
    seed_bytes = b'modlpy/utilisuba'

    root_account_bytes = bytes.fromhex(Keypair(root_account).public_key[2:])
    index_bytes = int(index).to_bytes(2, 'little')

    entropy = blake2b(seed_bytes + root_account_bytes + index_bytes, digest_size=32).digest()
    input_bytes = bytes([42]) + entropy
    checksum = blake2b(b'SS58PRE' + input_bytes).digest()
    return base58.b58encode(input_bytes + checksum[:2]).decode()


project.load(Path.home() / ".brownie" / "packages" / config["dependencies"][0])
if hasattr(project, 'OpenzeppelinContracts410Project'):
    OpenzeppelinContractsProject = project.OpenzeppelinContracts410Project
else:
    OpenzeppelinContractsProject = project.OpenzeppelinContractsProject


def load_deployments(network):
    path = './deployments/' + network + '.json'
    if Path(path).is_file():
        with open(path) as file:
            return json.load(file)
    else:
        return {}


def save_deployments(deployments, network):
    deployments_dir = './deployments/'
    if not os.path.exists(deployments_dir):
        os.mkdir(deployments_dir)
    path = deployments_dir + network + '.json'
    with open(path, 'w+') as file:
        json.dump(deployments, file)


def load_deployment_config(network):
    with open('./deployment-config.yml') as file:
        return yaml.safe_load(file)['networks'][network]


CONFIG = load_deployment_config(NETWORK)
DEPLOYMENTS = load_deployments(NETWORK)


# global configs
CONFS = 1
GAS_PRICE = "100 gwei"
GAS_LIMIT = 10*10**6



# utils
def ss58decode(address):
    return Keypair(ss58_address=address).public_key


def get_opts(sender, gas_price=GAS_PRICE, gas_limit=GAS_LIMIT):
    return {'from': sender, 'gas_price': gas_price, 'gas_limit': gas_limit}


def get_deployment(container):
    info = container.get_verification_info()
    name = info['contract_name']
    if name in DEPLOYMENTS:
        return DEPLOYMENTS[name]
    else:
        return None


def add_new_deploy(container, address):
    info = container.get_verification_info()
    name = info['contract_name']
    DEPLOYMENTS[name] = address
    save_deployments(DEPLOYMENTS, NETWORK)


def yes_or_no(question):
    reply = input(question+' (y/n): ').lower().strip()
    if reply[0] == 'y':
        return True
    if reply[0] == 'n':
        return False
    else:
        return yes_or_no(Fore.RED + "Uhhhh... please enter y/n ")

def check_and_get_deployment(container):
    deployment = get_deployment(container)
    name = container.get_verification_info()["contract_name"]
    if deployment:
        if yes_or_no(Fore.RED + f'Found old deployment for {name} at {deployment}, use it?'):
            return container.at(deployment)
        else:
            print(Fore.RED + f'REDEPLOYING {name} contract to new address')
    return None


def deploy_with_proxy(container, proxy_admin, deployer, *args):
    print("")

    deployment = check_and_get_deployment(container)
    if deployment:
        return deployment

    name = container.get_verification_info()["contract_name"]
    print(Fore.GREEN + f'DEPLOYING {name} ...')

    owner = proxy_admin.owner()
    _implementation = container.deploy(get_opts(deployer))
    encoded_inputs = _implementation.initialize.encode_input(*args)

    _instance = OpenzeppelinContractsProject.TransparentUpgradeableProxy.deploy(
        _implementation,
        proxy_admin,
        encoded_inputs,
        get_opts(deployer)
    )
    OpenzeppelinContractsProject.TransparentUpgradeableProxy.remove(_instance)

    add_new_deploy(container, _instance.address)
    print(Fore.GREEN + f'Contract {name} deployed at {Fore.YELLOW}{_instance.address} {Fore.GREEN}under {Fore.RED} proxy')
    return container.at(_instance.address)


def deploy(container, deployer, *args):
    print("")

    deployment = check_and_get_deployment(container)
    if deployment:
        return deployment

    name = container.get_verification_info()["contract_name"]
    print(Fore.GREEN + f'DEPLOYING {name} ...')

    inst = None
    if args:
        inst = container.deploy(*args, get_opts(deployer))
    else:
        inst = container.deploy(get_opts(deployer))

    add_new_deploy(container, inst.address)
    print(Fore.GREEN + f'Contract {name} deployed at {Fore.YELLOW}{inst.address}')

    return inst


# deploy functions
def deploy_proxy_admin(deployer):
    return deploy(OpenzeppelinContractsProject.ProxyAdmin, deployer)


def deploy_auth_manager(deployer, proxy_admin, auth_super_admin):
    return deploy_with_proxy(AuthManager, proxy_admin, deployer, auth_super_admin)


def deploy_oracle_clone(deployer):
    return deploy(Oracle, deployer)


def deploy_oracle_master(deployer, proxy_admin, oracle_clone, oracle_quorum):
    return deploy_with_proxy(OracleMaster, proxy_admin, deployer, oracle_clone, oracle_quorum)


def deploy_withdrawal(deployer, proxy_admin, cap, xcTOKEN):
    return deploy_with_proxy(Withdrawal, proxy_admin, deployer, cap, xcTOKEN)


def deploy_ledger_clone(deployer):
    return deploy(Ledger, deployer)


def deploy_controller(deployer, proxy_admin, root_derivative_index, xc_token, relay_encoder, xcm_transactor, x_token, hex1, hex2, as_derevative_hex):
    return deploy_with_proxy(Controller, proxy_admin, deployer, root_derivative_index, xc_token, relay_encoder, xcm_transactor, x_token, hex1, hex2, as_derevative_hex)


def deploy_nimbus(
    deployer, proxy_admin, auth_manager, xc_token, controller,
    treasury, developers, oracle_master, withdrawal, deposit_cap,
    max_difference, token_name, token_symbol, token_decimals):
    return deploy_with_proxy(
        Nimbus, proxy_admin, deployer, auth_manager, xc_token, controller,
        developers, treasury, oracle_master, withdrawal, deposit_cap,
        max_difference, token_name, token_symbol, token_decimals
    )

def deploy_ledger_beacon(deployer, _ledger_clone, _nimbus):
    return deploy(LedgerBeacon, deployer, _ledger_clone, _nimbus)

def deploy_leger_factory(deployer, _nimbus, _ledger_beacon):
    return deploy(LedgerFactory, deployer, _nimbus, _ledger_beacon)


# deployment
def main():
    # TODO: update deploy script
    # TODO: update deployment config
    #deployer = accounts.at(CONFIG['deployer'])
    deployer = accounts.load(CONFIG['deployer'])

    auth_super_admin = CONFIG['auth_sudo']
    treasury = CONFIG['treasury']
    developers = CONFIG['developers']

    roles = CONFIG['roles']
    oracles = CONFIG['oracles']
    oracle_quorum = CONFIG['quorum']
    xc_token = CONFIG['precompiles']['xc_token']
    xcm_transactor = CONFIG['precompiles']['xcm_transactor']
    relay_encoder = CONFIG['precompiles']['relay_encoder']
    x_token = CONFIG['precompiles']['x_token']

    era_sec = CONFIG['relay_spec']['era_duratation']
    max_validators_per_ledger = CONFIG['relay_spec']['max_validators_per_ledger']
    min_nominator_bond = CONFIG['relay_spec']['min_nominator_bond']
    min_active_balance = CONFIG['relay_spec']['min_active_balance']
    reverse_transfer_fee = CONFIG['relay_spec']['reverse_transfer_fee']
    transfer_fee = CONFIG['relay_spec']['transfer_fee']
    max_unlocking_chunks = CONFIG['relay_spec']['max_unlocking_chunks']
    withdrawal_cap = CONFIG['withdrawal_cap']
    deposit_cap = CONFIG['deposit_cap']

    token_name = CONFIG['token_name']
    token_symbol = CONFIG['token_symbol']
    token_decimals = CONFIG['token_decimals']

    hex1 = CONFIG['hex1']
    hex2 = CONFIG['hex2']
    as_derevative_hex = CONFIG['as_derevative_hex']

    max_difference = CONFIG['oracle_limit']

    root_derivative_index = CONFIG['root_derivative_index']
    root_derivative_account = ss58decode(get_derivative_account(CONFIG['sovereign_account'], root_derivative_index))
    print(f'{Fore.GREEN}Root derivative account: {root_derivative_account}')

    stash_idxs = CONFIG['stash_indexes']
    stashes = [ss58decode(get_derivative_account(root_derivative_account, idx)) for idx in stash_idxs]
    print(f'{Fore.GREEN}Stash accounts: {stashes}')

    xcm_max_weight = CONFIG['xcm_max_weight']
    xcm_weights = CONFIG['xcm_weights']


    proxy_admin = deploy_proxy_admin(deployer)

    controller = deploy_controller(deployer, proxy_admin, root_derivative_index, xc_token, relay_encoder, xcm_transactor, x_token, hex1, hex2, as_derevative_hex)

    auth_manager = deploy_auth_manager(deployer, proxy_admin, auth_super_admin)

    for role in roles:
        print(f"{Fore.GREEN}Setting role: {role}")
        if auth_manager.has(web3.solidityKeccak(["string"], [role]), roles[role]):
            print(f"{Fore.YELLOW}Role {role} already setted, skipping..")
        else:
            auth_manager.addByString(role, roles[role], get_opts(deployer))

    oracle_clone = deploy_oracle_clone(deployer)

    oracle_master = deploy_oracle_master(deployer, proxy_admin, oracle_clone, oracle_quorum)

    withdrawal = deploy_withdrawal(deployer, proxy_admin, withdrawal_cap, xc_token)

    nimbus = deploy_nimbus(
        deployer, proxy_admin, auth_manager, xc_token, controller,
        treasury, developers, oracle_master, withdrawal, deposit_cap,
        max_difference, token_name, token_symbol, token_decimals
    )

    print(f"\n{Fore.GREEN}Configuring controller...")
    controller.setNimbus(nimbus, get_opts(deployer))
    controller.setMaxWeight(xcm_max_weight, get_opts(roles['ROLE_CONTROLLER_MANAGER']))
    controller.setWeights([w | (1<<65) for w in xcm_weights], get_opts(roles['ROLE_CONTROLLER_MANAGER']))
    controller.setReverseTransferFee(reverse_transfer_fee, get_opts(roles['ROLE_CONTROLLER_MANAGER']))
    controller.setTransferFee(transfer_fee, get_opts(roles['ROLE_CONTROLLER_MANAGER']))

    ledger_clone = deploy_ledger_clone(deployer)

    ledger_beacon = deploy_ledger_beacon(deployer, ledger_clone, nimbus)

    ledger_factory = deploy_leger_factory(deployer, nimbus, ledger_beacon)

    print(f'\n{Fore.GREEN}Nimbus configuration...')
    nimbus.setLedgerBeacon(ledger_beacon, get_opts(roles['ROLE_BEACON_MANAGER']))
    nimbus.setLedgerFactory(ledger_factory, get_opts(roles['ROLE_BEACON_MANAGER']))
    nimbus.setRelaySpec((max_validators_per_ledger, min_nominator_bond, min_active_balance, max_unlocking_chunks), get_opts(roles['ROLE_SPEC_MANAGER']))
    oracle_master.setAnchorEra(0, 1, era_sec, get_opts(roles['ROLE_SPEC_MANAGER']))

    print(f'\n{Fore.GREEN}Adding oracle members...')
    for oracle in oracles:
        print(f"{Fore.YELLOW}Adding oracle member: {oracle}")
        oracle_master.addOracleMember(oracle, get_opts(roles['ROLE_ORACLE_MEMBERS_MANAGER']))

    ledgers = []
    print(f'\n{Fore.GREEN}Adding ledgers...')
    for i in range(len(stashes)):
        s_bytes = ss58decode(stashes[i])
        print(f"{Fore.GREEN}Added ledger, idx: {stash_idxs[i]} stash: {stashes[i]}")
        nimbus.addLedger(s_bytes, s_bytes, stash_idxs[i], get_opts(roles['ROLE_LEDGER_MANAGER']))
        ledgers.append(nimbus.findLedger(s_bytes))

    for ledger in ledgers:
        print("Refreshing allowances for ledger:", ledger)
        Ledger.at(ledger).refreshAllowances(get_opts(roles['ROLE_LEDGER_MANAGER']))

    print(f'\n{Fore.GREEN}Sending xcTOKEN to Controller...')
    xc_token_contract = xcTOKEN_mock.at(xc_token)
    xc_token_contract.transfer(controller, CONFIG['controller_initial_balance'], get_opts(deployer))



def prompt():
    pass
