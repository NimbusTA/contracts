// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
pragma abicoder v2;

import "@openzeppelin/contracts/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import "./utils/WithdrawalQueue.sol";
import "../interfaces/INimbus.sol";

contract Withdrawal is Initializable {
    using WithdrawalQueue for WithdrawalQueue.Queue;

    // Element removed from queue
    event ElementRemoved(uint256 elementId);

    // Element added to queue
    event ElementAdded(uint256 elementId);

    // New redeem request added
    event RedeemRequestAdded(address indexed user, uint256 shares, uint256 batchId);

    // xcTOKEN claimed by user
    event Claimed(address indexed user, uint256 claimedAmount);

    // Losses ditributed to contract
    event LossesDistributed(uint256 losses);

    // nTOKEN smart contract
    INimbus public nTOKEN;

    // xcTOKEN precompile
    IERC20 public XCTOKEN;

    // withdrawal queue
    WithdrawalQueue.Queue public queue;

    // batch id => price for pool shares to xcTOKEN
    // to retrive xcTOKEN amount for user: user_pool_shares * batchSharePrice[batch_id]
    mapping(uint256 => uint256) public batchSharePrice;

    struct Request {
        uint256 share;
        uint256 batchId;
    }

    // user's withdrawal requests (unclaimed)
    mapping(address => Request[]) public userRequests;

    // total virtual xcTOKEN amount on contract
    uint256 public totalVirtualXcTokenAmount;

    // total amount of xcTOKEN pool shares
    uint256 public totalXcTokenPoolShares;

    // nTOKEN(xcTOKEN) virtual amount for batch
    uint256 public batchVirtualXcTokenAmount;

    // total shares for batch
    uint256 public batchShares;

    // Last Id of queue element which can be claimed
    uint256 public claimableId;

    // Balance for claiming
    uint256 public pendingForClaiming;

    // max amount of requests in parallel
    uint16 internal constant MAX_REQUESTS = 20;


    modifier onlyNimbus() {
        require(msg.sender == address(nTOKEN), "WITHDRAWAL: CALLER_NOT_NIMBUS");
        _;
    }

    /**
    * @notice Initialize redeemPool contract.
    * @param _cap - cap for queue
    * @param _xcTOKEN - xcTOKEN precompile address
    */
    function initialize(
        uint256 _cap,
        address _xcTOKEN
    ) external initializer {
        require(_cap > 0, "WITHDRAWAL: INCORRECT_CAP");
        require(_xcTOKEN != address(0), "WITHDRAWAL: INCORRECT_XCTOKEN_ADDRESS");
        queue.init(_cap);
        XCTOKEN = IERC20(_xcTOKEN);
    }

    /**
    * @notice Set nTOKEN contract address, allowed to only once
    * @param _nTOKEN nTOKEN contract address
    */
    function setNTOKEN(address _nTOKEN) external {
        require(address(nTOKEN) == address(0), "WITHDRAWAL: NTOKEN_ALREADY_DEFINED");
        require(_nTOKEN != address(0), "WITHDRAWAL: INCORRECT_NTOKEN_ADDRESS");

        nTOKEN = INimbus(_nTOKEN);
    }

    /**
    * @notice Burn pool shares from first element of queue and move index for allow claiming. After that add new batch
    */
    function newEra() external onlyNimbus {
        uint256 newXcTokenAmount = XCTOKEN.balanceOf(address(this)) - pendingForClaiming;

        if ((newXcTokenAmount > 0) && (queue.size > 0)) {
            (WithdrawalQueue.Batch memory topBatch, uint256 topId) = queue.top();
            // batchSharePrice = pool_xcTOKEN_balance / pool_shares
            // when user try to claim: user_TOKEN = user_pool_share * batchSharePrice
            uint256 sharePriceForBatch = getBatchSharePrice(topBatch);
            uint256 xcTokenForBatch = topBatch.batchTotalShares * sharePriceForBatch / 10**nTOKEN.decimals();
            if (newXcTokenAmount >= xcTokenForBatch) {
                batchSharePrice[topId] = sharePriceForBatch;

                totalXcTokenPoolShares -= topBatch.batchXcTokenShares;
                totalVirtualXcTokenAmount -= xcTokenForBatch;
                // NOTE: In case when losses occur due to rounding it is possible to
                // totalVirtualXcTokenAmount > 0 and totalXcTokenPoolShares = 0
                if (totalXcTokenPoolShares == 0) {
                    totalVirtualXcTokenAmount = 0;
                }

                claimableId = topId;
                pendingForClaiming += xcTokenForBatch;

                queue.pop();

                emit ElementRemoved(topId);
            }
        }

        if ((batchVirtualXcTokenAmount > 0) && (queue.size < queue.cap)) {
            uint256 batchTokenPoolShares = getTokenPoolShares(batchVirtualXcTokenAmount);

            WithdrawalQueue.Batch memory newBatch = WithdrawalQueue.Batch(batchShares, batchTokenPoolShares);
            uint256 newId = queue.push(newBatch);

            totalVirtualXcTokenAmount += batchVirtualXcTokenAmount;
            totalXcTokenPoolShares += batchTokenPoolShares;

            batchVirtualXcTokenAmount = 0;
            batchShares = 0;

            emit ElementAdded(newId);
        }
    }

    /**
    * @notice Returns total virtual xcTOKEN balance of contract for which losses can be applied
    */
    function totalBalanceForLosses() external view returns (uint256) {
        return totalVirtualXcTokenAmount + batchVirtualXcTokenAmount;
    }

    /**
    * @notice function returns xcTOKEN amount that should be available for claiming after batch remove
    * @param _batchShift batch shift from first element
    */
    function getXcTokenBalanceForBatch(uint256 _batchShift) external view returns (uint256) {
        (WithdrawalQueue.Batch memory specificBatch, ) = queue.element(_batchShift);
        // batchSharePrice = pool_xcTOKEN_balance / pool_shares
        // when user try to claim: user_TOKEN = user_pool_share * batchSharePrice
        uint256 sharePriceForBatch = getBatchSharePrice(specificBatch);
        uint256 xcTokenForBatch = specificBatch.batchTotalShares * sharePriceForBatch / 10**nTOKEN.decimals();
        return xcTokenForBatch;
    }

    /**
    * @notice function returns specific batch from queue
    * @param _batchShift batch shift from first element
    */
    function getQueueBatch(uint256 _batchShift) external view returns (WithdrawalQueue.Batch memory) {
        (WithdrawalQueue.Batch memory specificBatch, ) = queue.element(_batchShift);
        return specificBatch;
    }

    /**
    * @notice 1. Mint equal amount of pool shares for user
    * @notice 2. Adjust current amount of virtual xcTOKEN on Withdrawal contract
    * @notice 3. Burn shares on Nimbus side
    * @param _from user address for minting
    * @param _amount amount of nTOKEN which user wants to redeem
    */
    function redeem(address _from, uint256 _amount) external onlyNimbus {
        // NOTE: user share in batch = user nTOKEN balance in specific batch
        require(userRequests[_from].length < MAX_REQUESTS, "WITHDRAWAL: REQUEST_CAP_EXCEEDED");
        uint256 userShares = _getBatchShares(_amount);
        batchShares += userShares;

        batchVirtualXcTokenAmount += _amount;

        Request memory req = Request(userShares, queue.nextId());
        userRequests[_from].push(req);

        emit RedeemRequestAdded(_from, req.share, req.batchId);
    }

    /**
    * @notice Returns available for claiming xcTOKEN amount for user
    * @param _holder user address for claiming
    */
    function claim(address _holder) external onlyNimbus returns (uint256) {
        // go through claims and check if unlocked than just transfer xcTOKENs
        uint256 readyToClaim = 0;
        uint256 readyToClaimCount = 0;
        Request[] storage requests = userRequests[_holder];
        uint256 nTokenDecimals = 10**nTOKEN.decimals();

        for (uint256 i = 0; i < requests.length; ++i) {
            if (requests[i].batchId <= claimableId) {
                readyToClaim += requests[i].share * batchSharePrice[requests[i].batchId] / nTokenDecimals;
                readyToClaimCount += 1;
            }
            else {
                requests[i - readyToClaimCount] = requests[i];
            }
        }

        // remove claimed items
        for (uint256 i = 0; i < readyToClaimCount; ++i) { requests.pop(); }

        require(readyToClaim <= XCTOKEN.balanceOf(address(this)), "WITHDRAWAL: CLAIM_EXCEEDS_BALANCE");
        XCTOKEN.transfer(_holder, readyToClaim);
        pendingForClaiming -= readyToClaim;

        emit Claimed(_holder, readyToClaim);

        return readyToClaim;
    }

    /**
    * @notice Apply losses to current nTOKEN shares on this contract
    * @param _losses user address for claiming
    */
    function ditributeLosses(uint256 _losses) external onlyNimbus {
        if (batchVirtualXcTokenAmount > 0) {
            uint256 xcTokenBalance = XCTOKEN.balanceOf(address(this));
            uint256 virtualBalance =
                totalVirtualXcTokenAmount + batchVirtualXcTokenAmount - (xcTokenBalance - pendingForClaiming);

            uint256 lossesForCurrentBatch = _losses * batchVirtualXcTokenAmount / virtualBalance;
            batchVirtualXcTokenAmount -= lossesForCurrentBatch;
            _losses -= lossesForCurrentBatch;
        }
        totalVirtualXcTokenAmount -= _losses;
        emit LossesDistributed(_losses);
    }

    /**
    * @notice Check available for claim xcTOKEN balance for user
    * @param _holder user address
    */
    function getRedeemStatus(address _holder) external view returns(uint256 _waiting, uint256 _available) {
        Request[] storage requests = userRequests[_holder];
        uint256 nTokenDecimals = 10**nTOKEN.decimals();

        for (uint256 i = 0; i < requests.length; ++i) {
            if (requests[i].batchId <= claimableId) {
                _available += requests[i].share * batchSharePrice[requests[i].batchId] / nTokenDecimals;
            }
            else {
                _waiting += requests[i].share * getBatchSharePrice(queue.findBatch(requests[i].batchId)) / nTokenDecimals;
            }
        }
        return (_waiting, _available);
    }

    /**
    * @notice Calculate share price to TOKEN for specific batch
    * @param _batch batch
    */
    function getBatchSharePrice(WithdrawalQueue.Batch memory _batch) internal view returns (uint256) {
        uint256 batchTokenPrice;
        if (totalXcTokenPoolShares > 0) {
            // user_TOKEN = user_batch_share * batch_share_price
            // batch_share_price = (1 / batch_total_shares) * batch_pool_shares * (total_xcTOKEN / total_pool_shares)
            if (_batch.batchTotalShares > 0) {
                batchTokenPrice = (10**nTOKEN.decimals() * _batch.batchXcTokenShares * totalVirtualXcTokenAmount) /
                                (_batch.batchTotalShares * totalXcTokenPoolShares);
            }
            else {
                // NOTE: This means that batch not added to queue currently
                if (batchVirtualXcTokenAmount > 0) {
                    batchTokenPrice = batchVirtualXcTokenAmount * 10**nTOKEN.decimals() / batchShares;
                }
            }
        }
        else {
            // NOTE: This means that we have only one batch that no in the pool
            if (batchVirtualXcTokenAmount > 0) {
                batchTokenPrice = batchVirtualXcTokenAmount * 10**nTOKEN.decimals() / batchShares;
            }
        }
        return batchTokenPrice;
    }

    /**
    * @notice Calculate shares amount in TOKEN pool for specific xcTOKEN amount
    * @param _amount amount of xcTOKEN tokens
    */
    function getTokenPoolShares(uint256 _amount) internal view returns (uint256) {
        if (totalVirtualXcTokenAmount > 0) {
            return _amount * totalXcTokenPoolShares / totalVirtualXcTokenAmount;
        }
        return _amount;
    }

    /**
    * @notice Function return shares of current batch for user
    * @param _amount amount of nTOKEN which user wants to redeem
    */
    function _getBatchShares(uint256 _amount) internal view returns (uint256) {
        if (batchVirtualXcTokenAmount > 0) {
            return _amount * batchShares / batchVirtualXcTokenAmount;
        }
        return _amount;
    }
}
