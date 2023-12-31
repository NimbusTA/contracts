// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/proxy/utils/Initializable.sol";

import "../interfaces/IRelayEncoder.sol";
import "../interfaces/IxTokens.sol";
import "../interfaces/IXcmTransactor.sol";
import "../interfaces/ILedger.sol";
import "../interfaces/IAuthManager.sol";
import "../interfaces/INimbus.sol";
import "./utils/Encoding.sol";


contract Controller is Initializable {
    using Encoding for uint256;

    // Event emitted when weight updated
    event WeightUpdated (
        uint8 index,
        uint64 newValue
    );

    // Event emitted when bond called on relay chain
    event Bond (
        address caller,
        bytes32 stash,
        bytes32 controller,
        uint256 amount
    );

    // Event emitted when bond extra called on relay chain
    event BondExtra (
        address caller,
        bytes32 stash,
        uint256 amount
    );

    // Event emitted when unbond on relay chain
    event Unbond (
        address caller,
        bytes32 stash,
        uint256 amount
    );

    // Event emitted when rebond called on relay chain
    event Rebond (
        address caller,
        bytes32 stash,
        uint256 amount
    );

    // Event emitted when withdraw called on relay chain
    event Withdraw (
        address caller,
        bytes32 stash
    );

    // Event emitted when nominate called on relay chain
    event Nominate (
        address caller,
        bytes32 stash,
        bytes32[] validators
    );

    // Event emitted when chill called on relay chain
    event Chill (
        address caller,
        bytes32 stash
    );

    // Event emitted when transfer xcTOKEN from parachain to relay chain called
    event TransferToRelaychain (
        address from,
        bytes32 to,
        uint256 amount
    );

    // Event emitted when transfer TOKEN from relay chain to parachain called
    event TransferToParachain (
        bytes32 from,
        address to,
        uint256 amount
    );

    // ledger controller account
    uint16 public rootDerivativeIndex;

    // xcTOKEN precompile
    IERC20 internal XCTOKEN;

    // relay call builder precompile
    IRelayEncoder internal RELAY_ENCODER;

    // xcm transactor precompile
    IXcmTransactor internal XCM_TRANSACTOR;

    // xTokens precompile
    IxTokens internal X_TOKENS;

    // Nimbus address
    address public Nimbus;

    // first hex for encodeTransfer (defines parachain ID, 2023 for Kusama)
    bytes public hex1;

    // second hex for encodeTransfer (defines asset for transfer, fungible)
    bytes public hex2;

    // hex for determination pallet (0x1801 for Kusama)
    bytes public asDerevativeHex;

    // Second layer derivative-proxy account to index
    mapping(address => uint16) public senderToIndex;

    // Index to second layer derivative-proxy account
    mapping(uint16 => bytes32) public indexToAccount;

    // Enumerator for weights
    enum WEIGHT {
        AS_DERIVATIVE,              // 362_006_000
        BOND_BASE,                  // 548_821_000
        BOND_EXTRA_BASE,            // 986_732_000
        UNBOND_BASE,                // 6_036_310_676
        WITHDRAW_UNBONDED_BASE,     // 1_610_727_324
        WITHDRAW_UNBONDED_PER_UNIT, // 100_942_386
        REBOND_BASE,                // 1_112_202_743
        REBOND_PER_UNIT,            // 47_309
        CHILL_BASE,                 // 861_822_000
        NOMINATE_BASE,              // 964_676_849
        NOMINATE_PER_UNIT,          // 27_639_322
        TRANSFER_TO_PARA_BASE,      // 1_100_000_000
        TRANSFER_TO_RELAY_BASE      // 4_000_000_000
    }

    // Constant for max weight
    uint64 public MAX_WEIGHT;// = 6_398_316_676;

    // Array with current weights
    uint64[] public weights;

    // Parachain side fee on reverse transfer
    uint256 public REVERSE_TRANSFER_FEE;// = 409_165_302

    // Relay side fee on transfer
    uint256 public TRANSFER_FEE;// = 250_000_000

    // Controller manager role
    bytes32 internal constant ROLE_CONTROLLER_MANAGER = keccak256("ROLE_CONTROLLER_MANAGER");

    // Beacon manager role
    bytes32 internal constant ROLE_BEACON_MANAGER = keccak256("ROLE_BEACON_MANAGER");

    // Allows function calls only for registered ledgers
    modifier onlyRegistred() {
        require(senderToIndex[msg.sender] != 0, "CONTROLLER: UNREGISTERED_SENDER");
        _;
    }

    // Allows function calls only for members with role
    modifier auth(bytes32 role) {
        require(IAuthManager(INimbus(Nimbus).AUTH_MANAGER()).has(role, msg.sender), "CONTROLLER: UNAUTHOROZED");
        _;
    }

    // Allows function calls only for Nimbus contract
    modifier onlyNimbus() {
        require(msg.sender == Nimbus, "CONTROLLER: CALLER_NOT_NIMBUS");
        _;
    }

    /**
    * @notice Initialize contoller contract.
    * @param _rootDerivativeIndex - registered id for sending XCM messages
    * @param _xcTOKEN - xcTOKEN contract address
    * @param _relayEncoder - relayEncoder(relaychain calls builder) contract address
    * @param _xcmTransactor - xcmTransactor(relaychain calls relayer) contract address
    * @param _xTokens - precompile for sending xc tokens to Relay chain
    * @param _hex1 - first hex for encodeTransfer
    * @param _hex2 - second hex for encodeTransfer
    * @param _asDerevativeHex - hex for as derevative call
    */
    function initialize(
        uint16 _rootDerivativeIndex,
        address _xcTOKEN,
        address _relayEncoder,
        address _xcmTransactor,
        address _xTokens,
        bytes calldata _hex1,
        bytes calldata _hex2,
        bytes calldata _asDerevativeHex
    ) external initializer {
        require(address(XCTOKEN) == address(0), "CONTROLLER: ALREADY_INITIALIZED");

        rootDerivativeIndex = _rootDerivativeIndex;

        XCTOKEN = IERC20(_xcTOKEN);
        RELAY_ENCODER = IRelayEncoder(_relayEncoder);
        XCM_TRANSACTOR = IXcmTransactor(_xcmTransactor);
        X_TOKENS = IxTokens(_xTokens);

        hex1 = _hex1;
        hex2 = _hex2;
        asDerevativeHex = _asDerevativeHex;
    }

    /**
    * @notice Get current weight by enum
    * @param weightType - enum index of weight
    */
    function getWeight(WEIGHT weightType) public view returns(uint64) {
        return weights[uint256(weightType)];
    }

    /**
    * @notice Set new max weight. Can be called only by ROLE_CONTROLLER_MANAGER
    * @param _maxWeight - max weight
    */
    function setMaxWeight(uint64 _maxWeight) external auth(ROLE_CONTROLLER_MANAGER) {
        MAX_WEIGHT = _maxWeight;
    }

    /**
    * @notice Set new REVERSE_TRANSFER_FEE
    * @param _reverseTransferFee - new fee
    */
    function setReverseTransferFee(uint256 _reverseTransferFee) external auth(ROLE_CONTROLLER_MANAGER) {
        REVERSE_TRANSFER_FEE = _reverseTransferFee;
    }

    /**
    * @notice Set new TRANSFER_FEE
    * @param _transferFee - new fee
    */
    function setTransferFee(uint256 _transferFee) external auth(ROLE_CONTROLLER_MANAGER) {
        TRANSFER_FEE = _transferFee;
    }

    /**
    * @notice Set new relay encoder
    * @param _relayEncoder - new relay encoder
    */
    function setRelayEncoder(address _relayEncoder) external auth(ROLE_BEACON_MANAGER) {
        require(_relayEncoder != address(0), "CONTROLLER: ENCODER_ZERO_ADDRESS");
        RELAY_ENCODER = IRelayEncoder(_relayEncoder);
    }

    /**
    * @notice Set new hexes parametes for encodeTransfer
    * @param _hex1 - first hex for encodeTransfer
    * @param _hex2 - second hex for encodeTransfer
    * @param _asDerevativeHex - hex for as derevative call
    */
    function updateHexParameters(bytes calldata _hex1, bytes calldata _hex2, bytes calldata _asDerevativeHex) external auth(ROLE_CONTROLLER_MANAGER) {
        hex1 = _hex1;
        hex2 = _hex2;
        asDerevativeHex = _asDerevativeHex;
    }

    /**
    * @notice Set Nimbus address. Function can be called only once
    * @param _nimbus - Nimbus address
    */
    function setNimbus(address _nimbus) external {
        require(Nimbus == address(0) && _nimbus != address(0), "CONTROLLER: NIMBUS_ALREADY_INITIALIZED");
        Nimbus = _nimbus;
    }

    /**
    * @notice Update weights array. Weight updated only if weight = _weight | 1 << 65
    * @notice _weights_i should be <= MAX_WEIGHT
    * @param _weights - weights array
    */
    function setWeights(
        uint128[] calldata _weights
    ) external auth(ROLE_CONTROLLER_MANAGER) {
        require(_weights.length == uint256(type(WEIGHT).max) + 1, "CONTROLLER: WRONG_WEIGHTS_SIZE");
        for (uint256 i = 0; i < _weights.length; ++i) {
            if ((_weights[i] >> 64) > 0) { // if _weights[i] = _weights[i] | 1 << 65 we must update i-th weight
                if (weights.length == i) {
                    weights.push(0);
                }

                require(uint64(_weights[i]) <= MAX_WEIGHT, "CONTROLLER: WRONG_WEIGHT");
                weights[i] = uint64(_weights[i]);
                emit WeightUpdated(uint8(i), weights[i]);
            }
        }
    }

    /**
    * @notice Register new ledger contract
    * @param index - index of ledger contract
    * @param accountId - relay chain address of ledger
    * @param paraAddress - parachain address of ledger
    */
    function newSubAccount(uint16 index, bytes32 accountId, address paraAddress) external onlyNimbus {
        require(indexToAccount[index + 1] == bytes32(0), "CONTROLLER: ALREADY_REGISTERED");

        senderToIndex[paraAddress] = index + 1;
        indexToAccount[index + 1] = accountId;
    }

    /**
    * @notice Unregister ledger contract
    * @param paraAddress - parachain address of ledger
    */
    function deleteSubAccount(address paraAddress) external onlyNimbus {
        require(senderToIndex[paraAddress] > 0, "CONTROLLER: UNREGISTERED_LEDGER");

        // NOTE: We do not deleting indexToAccount, so it is impossible to register new account with
        // index that was already used
        // delete indexToAccount[senderToIndex[paraAddress]];
        delete senderToIndex[paraAddress];
    }

    /**
    * @notice Nominate validators from ledger on relay chain
    * @param validators - validators addresses to nominate
    */
    function nominate(bytes32[] calldata validators) external onlyRegistred {
        uint256[] memory convertedValidators = new uint256[](validators.length);
        for (uint256 i = 0; i < validators.length; ++i) {
            convertedValidators[i] = uint256(validators[i]);
        }
        callThroughDerivative(
            getSenderIndex(),
            getWeight(WEIGHT.NOMINATE_BASE) + getWeight(WEIGHT.NOMINATE_PER_UNIT) * uint64(validators.length),
            RELAY_ENCODER.encode_nominate(convertedValidators)
        );

        emit Nominate(msg.sender, getSenderAccount(), validators);
    }

    /**
    * @notice Bond free TOKEN of ledger on relay chain
    * @param controller - controller which used to bond
    * @param amount - amount of TOKEN to bond
    */
    function bond(bytes32 controller, uint256 amount) external onlyRegistred {
        callThroughDerivative(
            getSenderIndex(),
            getWeight(WEIGHT.BOND_BASE),
            RELAY_ENCODER.encode_bond(uint256(controller), amount, bytes(hex"00"))
        );

        emit Bond(msg.sender, getSenderAccount(), controller, amount);
    }

    /**
    * @notice Bond extra TOKEN of ledger on relay chain
    * @param amount - extra amount of TOKEN to bond
    */
    function bondExtra(uint256 amount) external onlyRegistred {
        callThroughDerivative(
            getSenderIndex(),
            getWeight(WEIGHT.BOND_EXTRA_BASE),
            RELAY_ENCODER.encode_bond_extra(amount)
        );

        emit BondExtra(msg.sender, getSenderAccount(), amount);
    }

    /**
    * @notice Unbond TOKEN of ledger on relay chain (move active balance to unbonding chunks)
    * @param amount - amount of TOKEN to unbond
    */
    function unbond(uint256 amount) external onlyRegistred {
        callThroughDerivative(
            getSenderIndex(),
            getWeight(WEIGHT.UNBOND_BASE),
            RELAY_ENCODER.encode_unbond(amount)
        );

        emit Unbond(msg.sender, getSenderAccount(), amount);
    }

    /**
    * @notice Withdraw unbonded tokens (move unbonded tokens to free)
    * @param slashingSpans - number of slashes received by ledger in case if we trying to set
    ledger bonded balance < min, in other cases = 0
    */
    function withdrawUnbonded(uint32 slashingSpans) external onlyRegistred {
        callThroughDerivative(
            getSenderIndex(),
            getWeight(WEIGHT.WITHDRAW_UNBONDED_BASE) + getWeight(WEIGHT.WITHDRAW_UNBONDED_PER_UNIT) * slashingSpans,
            RELAY_ENCODER.encode_withdraw_unbonded(slashingSpans)
        );

        emit Withdraw(msg.sender, getSenderAccount());
    }

    /**
    * @notice Rebond TOKEN of ledger from unbonded chunks on relay chain
    * @param amount - amount of TOKEN to rebond
    * @param unbondingChunks - amount of unbonding chunks to rebond
    */
    function rebond(uint256 amount, uint256 unbondingChunks) external onlyRegistred {
        callThroughDerivative(
            getSenderIndex(),
            getWeight(WEIGHT.REBOND_BASE) + getWeight(WEIGHT.REBOND_PER_UNIT) * uint64(unbondingChunks),
            RELAY_ENCODER.encode_rebond(amount)
        );

        emit Rebond(msg.sender, getSenderAccount(), amount);
    }

    /**
    * @notice Put ledger to chill mode
    */
    function chill() external onlyRegistred {
        callThroughDerivative(
            getSenderIndex(),
            getWeight(WEIGHT.CHILL_BASE),
            RELAY_ENCODER.encode_chill()
        );

        emit Chill(msg.sender, getSenderAccount());
    }

    /**
    * @notice Transfer TOKEN from relay chain to parachain
    * @param amount - amount of TOKEN to transfer
    */
    function transferToParachain(uint256 amount) external onlyRegistred {
        // to - msg.sender, from - getSenderIndex()
        uint256 parachain_fee = REVERSE_TRANSFER_FEE;

        callThroughDerivative(
            getSenderIndex(),
            getWeight(WEIGHT.TRANSFER_TO_PARA_BASE),
            encodeLimitReserveTransfer(msg.sender, amount, getWeight(WEIGHT.TRANSFER_TO_PARA_BASE))
        );

        // compensate parachain side fee on reverse transfer
        if (amount <= parachain_fee) {
            // if amount less than fee just transfer amount
            XCTOKEN.transfer(msg.sender, amount);
        }
        else {
            // else just compensate fee
            XCTOKEN.transfer(msg.sender, parachain_fee);
        }

        emit TransferToParachain(getSenderAccount(), msg.sender, amount);
    }

    /**
    * @notice Transfer xcTOKEN from parachain to relay chain
    * @param amount - amount of xcTOKEN to transfer
    */
    function transferToRelaychain(uint256 amount) external onlyRegistred {
        // to - getSenderIndex(), from - msg.sender
        XCTOKEN.transferFrom(msg.sender, address(this), amount);
        IxTokens.Multilocation memory destination;
        destination.parents = 1;
        destination.interior = new bytes[](1);
        destination.interior[0] = bytes.concat(bytes1(hex"01"), getSenderAccount(), bytes1(hex"00")); // X2, NetworkId: Any
        X_TOKENS.transfer_with_fee(address(XCTOKEN), amount, TRANSFER_FEE, destination, getWeight(WEIGHT.TRANSFER_TO_RELAY_BASE));

        emit TransferToRelaychain(msg.sender, getSenderAccount(), amount);
    }

    /**
    * @notice Get index of registered ledger
    */
    function getSenderIndex() internal returns(uint16) {
        return senderToIndex[msg.sender] - 1;
    }

    /**
    * @notice Get relay chain address of msg.sender
    */
    function getSenderAccount() internal returns(bytes32) {
        return indexToAccount[senderToIndex[msg.sender]];
    }

    /**
    * @notice Send call to relay cahin through xcm transactor
    * @param index - index of ledger on relay chain
    * @param weight - fees on tx execution
    * @param call - bytes for tx execution
    */
    function callThroughDerivative(uint16 index, uint64 weight, bytes memory call) internal {
        bytes memory le_index = new bytes(2);
        le_index[0] = bytes1(uint8(index));
        le_index[1] = bytes1(uint8(index >> 8));

        uint64 total_weight = weight + getWeight(WEIGHT.AS_DERIVATIVE);
        require(total_weight <= MAX_WEIGHT, "CONTROLLER: TOO_MUCH_WEIGHT");

        XCM_TRANSACTOR.transact_through_derivative(
            0, // The transactor to be used
            rootDerivativeIndex, // The index to be used
            address(XCTOKEN), // Address of the currencyId of the asset to be used for fees
            total_weight, // The weight we want to buy in the destination chain
            bytes.concat(asDerevativeHex, le_index, call) // The inner call to be executed in the destination chain
        );
    }

    /**
    * @notice Encoding bytes to call transfer on relay chain
    * @param to - address of TOKEN receiver
    * @param amount - amount of TOKEN to send
    */
    function encodeReverseTransfer(address to, uint256 amount) internal returns(bytes memory) {
        return bytes.concat(
            hex1,
            abi.encodePacked(to),
            hex2,
            amount.scaleCompactUint(),
            hex"00000000"
        );
    }

    /**
    * @notice Encoding bytes to call limit reserve transfer on relay chain
    * @param to - address of TOKEN receiver
    * @param amount - amount of TOKEN to send
    * @param weight - weight for xcm call
    */
    function encodeLimitReserveTransfer(address to, uint256 amount, uint64 weight) internal returns(bytes memory) {
        return bytes.concat(
            hex1,
            abi.encodePacked(to),
            hex2,
            amount.scaleCompactUint(),
            hex"0000000001",
            uint256(weight).scaleCompactUint(),
            hex"00"
        );
    }
}
