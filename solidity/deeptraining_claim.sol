// SPDX-License-Identifier: MIT
// File: Hackathon_deeptraining_claim.sol

pragma solidity ^0.8.0;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract WhiteList is Ownable {
    constructor() Ownable(msg.sender) {}

    mapping (address => bool) public isWhitelisted;
    modifier onlyWhitelisted() {
        require(isWhitelisted[msg.sender], "not whitelisted");
        _;
    }
    event AddedWhiteList(address _user);
    event RemovedWhiteList(address _user);
    // Contract owner: Add address to whitelist
    function addWhiteList (address _addr) public onlyOwner {
        require(!isWhitelisted[_addr], "Address already whitelisted");
        isWhitelisted[_addr] = true;
        emit AddedWhiteList(_addr);
    }
    // Contract owner: Remove address from whitelist
    function removeWhiteList (address _addr) public onlyOwner {
        require(isWhitelisted[_addr], "Address not whitelisted");
        isWhitelisted[_addr] = false;
        emit RemovedWhiteList(_addr);
    }
    function getWhiteListStatus(address _maker) external view returns (bool) {
        return isWhitelisted[_maker];
    }
}
interface Ideeptraining {
    function Issue() external view returns (uint256); // Current issue number
    function IssueEmotion(uint256 _Issue) external view returns (uint256); // Query winning emotion for specific issue
    function IssueReward(uint256 _Issue) external view returns (uint256); // Query reward amount for specific issue
    function IssueAddressEmotions(uint256 _Issue, address _addr) external view returns (uint256); // Query address emotion for specific issue
}
contract ClaimAward is WhiteList {
    address public USDC;  // USDC contract address
    Ideeptraining public deeptraining; // Training contract address
    mapping(address => uint256) public AddressReceiveIssue; // Last claimed issue per address

    event Claimed(address, uint256);
    
    constructor(address _USDC, Ideeptraining _deeptraining){
        USDC = _USDC;  // Set USDC contract address
        deeptraining = _deeptraining; // Set deeptraining contract address
    }

    // Calculate unclaimed rewards
    function getReward(address _addr) public view returns(uint256){
        require(_addr != address(0), "Invalid address");
        uint256 totalAward;
        uint256 lastClaimedIssue = AddressReceiveIssue[_addr];
        uint256 currentIssue = deeptraining.Issue();

        for (uint i = lastClaimedIssue + 1; i <= currentIssue; i++) {
            if(deeptraining.IssueAddressEmotions(i, _addr) == deeptraining.IssueEmotion(i)){
                totalAward += deeptraining.IssueReward(i);
            }
        }
        return totalAward;
    }
    // Claim accumulated rewards
    function claim() public {
        uint256 totalAward =  getReward(msg.sender);
        require(totalAward > 0, "Insufficient rewards");
        require(totalAward <= ERC20(USDC).balanceOf(address(this)), "Insufficient contract balance");

        uint256 currentIssue = deeptraining.Issue();
        // Update last claimed issue: current if drawn, else previous
        AddressReceiveIssue[msg.sender] = deeptraining.IssueEmotion(currentIssue) > 0 ? currentIssue : currentIssue - 1;

        ERC20(USDC).transfer(msg.sender, totalAward);
        emit Claimed(msg.sender, totalAward);
    }
    // Whitelist user: Transfer tokens
    function transferToken(address _token, address _recipient, uint256 _amount) public onlyWhitelisted {
        ERC20(_token).transfer(_recipient, _amount);
    }
    // Contract owner: Update USDC address
    function setUSDCAddress(address _usdc) public onlyOwner {
        require(_usdc != address(0), "Invalid USDC address");
        USDC = _usdc;
    }
    // Contract owner: Update deeptraining contract
    function setdeeptraining(Ideeptraining _addr)public onlyOwner{
        deeptraining = _addr;
    }
}