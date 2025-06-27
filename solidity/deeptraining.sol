// SPDX-License-Identifier: MIT
// File: Hackathon_deeptraining.sol

pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
// Chainlink VRF
import {IVRFCoordinatorV2Plus} from "@chainlink/contracts@1.4.0/src/v0.8/vrf/dev/interfaces/IVRFCoordinatorV2Plus.sol";
import {VRFConsumerBaseV2Plus} from "@chainlink/contracts@1.4.0/src/v0.8/vrf/dev/VRFConsumerBaseV2Plus.sol";
import {VRFV2PlusClient} from "@chainlink/contracts@1.4.0/src/v0.8/vrf/dev/libraries/VRFV2PlusClient.sol";

contract deeptraining is VRFConsumerBaseV2Plus {
    // Whitelist
    mapping(address => bool) public isWhitelisted;
    modifier onlyWhitelisted() {
        require(isWhitelisted[msg.sender], "not whitelisted");
        _;
    }
    event AddedWhiteList(address _user);
    event RemovedWhiteList(address _user);

    uint256 public Issue; // Current issue number
    address public USDC;  // USDC contract address
    address public Recipient; // Recipient address
    uint8 public userProportion; // User proportion

    // Chainlink VRF V2.5
    IVRFCoordinatorV2Plus private immutable i_vrfCoordinator; // VRF coordinator address
    bytes32 private s_keyHash;                                // VRF gas lane key hash
    uint256 private s_subscriptionId;                         // Subscription ID
    uint256 private s_requestId;
    // Chainlink VRF constants
    uint16 private constant REQUEST_CONFIRMATIONS = 3;
    uint32 private constant CALLBACK_GAS_LIMIT = 400000;
    uint32 private constant NUM_WORDS = 1;
    uint256 private constant VRF_IN_PROGRESS = 42;
    
    struct information{
        uint256 duration; // End timestamp
        uint256 price;    // Price per training
        uint256 putmoney; // Seed funding
    }
    information public pendingNewIssue;

    mapping(uint256 => information)public IssueInformation; // Issue information mapping
    mapping(uint256 => uint256)public IssueAddressNum; // Participant count per issue
    mapping(uint256 => uint256)public IssueReward;  // Reward amount per issue
    mapping(uint256 => uint256)public IssueEmotion; // Emotion result per issue
    mapping(uint256 => mapping(address => bool))public IssueAddrEmo; // Participation status
    mapping(uint256 => mapping(address => uint8)) public IssueAddressEmotions; // Address emotion per issue
    mapping(uint256 => mapping(uint256 => address[]))public IssueEmotionAddrs; // Addresses per emotion

    event Emotions(uint256, uint8, address);
    event OpenVrfInitiated(uint256 indexed issue, uint256 requestId); // VRF initiation event
    event OpenVrfCompleted(uint256 indexed issue, uint256 requestId, uint256 emotionResult); // VRF completion event
    event OpenEmotions(uint256 indexed issue, uint256 usertotal, uint256 useraverage); // Reward distribution event

    constructor(
        uint8 _userProportion,
        address _USDC,
        address _Recipient,
        // Chainlink VRF parameters
        address vrfCoordinator,
        bytes32 keyHash,
        uint256 subscriptionId
    )
        VRFConsumerBaseV2Plus(vrfCoordinator)
    {
        // Set proportion
        require(_userProportion >= 1 && _userProportion <= 100, "Invalid Proportion");
        userProportion = _userProportion;
        // Set address
        require(_USDC != address(0), "Invalid USDC address");
        USDC = _USDC;
        Recipient = _Recipient;
        // Chainlink VRF
        require(vrfCoordinator != address(0), "Invalid VRFCoordinator address");
        require(subscriptionId != 0, "Invalid subscription ID");
        i_vrfCoordinator = IVRFCoordinatorV2Plus(vrfCoordinator);
        s_keyHash = keyHash;
        s_subscriptionId = subscriptionId;
        // whitelist
        isWhitelisted[msg.sender] = true;
    }

    // Deep training: 0=Not trained, 1=Positive, 2=Neutral, 3=Negative
    function emotions(address _addr, uint8 _num) public {
        require(Issue != 0, "No active issue");
        require(IssueAddrEmo[Issue][_addr] != true); // Prevent duplicate participation
        require(block.timestamp <= IssueInformation[Issue].duration, "This issue has ended");
        require(_num >= 1 && _num <= 3, "Invalid emotion");

        uint256 price = IssueInformation[Issue].price;
        require(ERC20(USDC).allowance(msg.sender, address(this)) >= price, "Insufficient allowance");
        require(ERC20(USDC).balanceOf(msg.sender) >= price, "Insufficient balance");

        IssueAddressNum[Issue] = IssueAddressNum[Issue] + 1; // Increment participant count
        IssueAddressEmotions[Issue][_addr] = _num; // Record emotion
        IssueEmotionAddrs[Issue][_num].push(_addr); // Add to emotion group
        IssueAddrEmo[Issue][_addr] = true; // Mark as participated

        ERC20(USDC).transferFrom(msg.sender, Recipient, price); // Transfer payment

        emit Emotions(Issue, _num, _addr);
    }
    // Get participant count for specific emotion
    function getIssueEmotionAddrslength(uint256 _Issue, uint256 _num) public view returns(uint256){
        return IssueEmotionAddrs[_Issue][_num].length;
    }

    // Whitelist user: Request random number
    function openVRFRandomEmotions() public onlyWhitelisted {
        require(block.timestamp >= IssueInformation[Issue].duration, "Not yet finished");
        require(IssueEmotion[Issue] == 0, "Emotions already exist");

        s_requestId = i_vrfCoordinator.requestRandomWords(
            VRFV2PlusClient.RandomWordsRequest({
                keyHash: s_keyHash,
                subId: s_subscriptionId,
                requestConfirmations: REQUEST_CONFIRMATIONS,
                callbackGasLimit: CALLBACK_GAS_LIMIT,
                numWords: NUM_WORDS,
                extraArgs: VRFV2PlusClient._argsToBytes(
                    VRFV2PlusClient.ExtraArgsV1({nativePayment: false})
                )
            })
        );
        IssueEmotion[Issue] = VRF_IN_PROGRESS;

        emit OpenVrfInitiated(Issue, s_requestId); 
    }
    // VRF coordinator callback
    function fulfillRandomWords(uint256 requestId, uint256[] calldata randomWords) internal override {
        uint256 emotionsresult = (randomWords[0] % 3) + 1; // Generate 1-3
        IssueEmotion[Issue] = emotionsresult;

        emit OpenVrfCompleted(Issue, requestId, emotionsresult);
    }

    // Whitelist user: Prize draw
    function openEmotions() public onlyWhitelisted {
        require(block.timestamp >= IssueInformation[Issue].duration, "Not yet finished");
        require(IssueEmotion[Issue] > 0, "Invalid emotion");
        require(IssueReward[Issue] == 0, "Reward already exists");

        uint256 emotionsresult = IssueEmotion[Issue] == VRF_IN_PROGRESS 
            ? uint256(keccak256(abi.encodePacked(blockhash(block.number - 1), msg.sender))) % 3 + 1
            : IssueEmotion[Issue];
        uint256 usertotal = IssueAddressNum[Issue] * IssueInformation[Issue].price * userProportion /100 + IssueInformation[Issue].putmoney;
        uint256 userpeople = IssueEmotionAddrs[Issue][emotionsresult].length;
        uint256 useraverage = userpeople != 0 ? usertotal / userpeople : 0;
        IssueReward[Issue] = useraverage; // Reward per winner

        emit OpenEmotions(Issue, usertotal, useraverage); 
    }
    // Whitelist user: Start new issue
    function openNewIssue(uint256 _duration, uint256 _price, uint256 _putmoney) public onlyWhitelisted {
        if (Issue > 0 && IssueReward[Issue] == 0) {
            // Prize draw
            openEmotions();
        }
        require(block.timestamp >= IssueInformation[Issue].duration, "Not yet finished");

        // Start new issue
        Issue = Issue + 1;
        IssueInformation[Issue] = information(block.timestamp + _duration, _price, _putmoney);
    }
    // Whitelist user: Set the award ratio
    function setProportion(uint8 newUserProportion) public onlyWhitelisted {
        require(newUserProportion >= 1 && newUserProportion <= 100, "Invalid Proportion");

        userProportion = newUserProportion;
    }
    // Contract owner: Update USDC address
    function setUSDCAddress(address _usdc) public onlyOwner {
        require(_usdc != address(0), "Invalid USDC address");
        USDC = _usdc;
    }
    // Contract owner: Update recipient address
    function setRecipientAddress(address _recipient) public onlyOwner {
        require(_recipient != address(0), "Invalid recipient address");
        Recipient = _recipient;
    }
    // Contract owner: Add address to whitelist
    function addWhitelist(address _addr) external onlyOwner {
        require(!isWhitelisted[_addr], "Address already whitelisted");
        isWhitelisted[_addr] = true;
        emit AddedWhiteList(_addr);
    }
    // Contract owner: Remove address from whitelist
    function removeWhitelist(address _addr) external onlyOwner {
        require(isWhitelisted[_addr], "Address not whitelisted");
        isWhitelisted[_addr] = false;
        emit RemovedWhiteList(_addr);
    }
    function getWhiteListStatus(address _addr) external view returns (bool) {
        return isWhitelisted[_addr];
    }
}