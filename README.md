# Nimbus Liquid Staking Protocol

The Nimbus Liquid Staking Protocol, built on Kusama(Polkadot) chain, allows their users to earn staking rewards on the Kusama chain without locking KSM or maintaining staking infrastructure.

Users can deposit KSM to the Nimbus smart contract and receive nKSM tokens in return. The smart contract then stakes tokens with the DAO-picked node operators. Users' deposited funds are pooled by the DAO, node operators never have direct access to the users' assets.

Unlike staked KSM directly on Kusama network, the nKSM token is free from the limitations associated with a lack of liquidity and can be transferred at any time.

Before getting started with this repo, please read:

## Contracts

Most of the protocol is implemented as a set of smart contracts.
These contracts are located in the [contracts/](contracts/) directory.

### [Nimbus](contracts/Nimbus.sol)
Main contract that implements stakes pooling, distribution logic and `nTOKEN` minting/burning mechanic.
Contract also inherits from `nTOKEN.sol` and impements ERC-20 interface for `nTOKEN` token.

### [nTOKEN](contracts/nTOKEN.sol)
The ERC20 token which uses shares to calculate users balances. A balance of a user depends on how much shares was minted and how much TOKEN was pooled to `Nimbus.sol`.

### [Ledger](contracts/Ledger.sol)
This contract contains staking logic of particular ledger. Basically, contract receive "target" stake amount from `Nimbus.sol` and current staking ledger state from relaychain and spawn XCM calls to relaychain to bring real ledger stake to "target" value.

### [Oracle](contracts/Oracle.sol)
Oracle contains logic to provide actual relaychain staking ledgers state to ledger contracts.
Contract uses consensus mechanism for protecting from malicious members, so in two words that require particular quorum from oracle members to report new state.

### [OracleMaster](contracts/OracleMaster.sol)
The hub for all oracles, which receives all reports from oracles members and simply sends them to oracles and also calls update of ledgers stakes in the `Nimbus.sol` when a new epoch begins.

### [Controller](contracts/Controller.sol)
Intermediate contract for interaction with relaychain through XCM. This contract basically incapsulate whole stuff about cross-chain communications and provide simple external interface for: calling relaychain's staking operations, bridging TOKEN from relaychain to parachain and back.

### [AuthManager](contracts/AuthManager.sol)
Simple contract which manages roles for the whole protocol. New and old roles can be added and removed.

### [LedgerFactory](contracts/LedgerFactory.sol)
The factory for creating new ledgers according the beacon proxy pattern. The beacon proxy allows to change an implementation for all proxies in one tx.


## Quick start
### Install dependencies

```bash=
pip install -r requirements.txt
```

### Compile contracts

```bash
brownie compile
```

### Run tests

```bash
brownie test
```

### Check coverage

```bash
brownie test --coverage
```