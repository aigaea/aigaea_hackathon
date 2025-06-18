import json
import time
from web3 import Web3

from config import WEB3_NETWORK, WEB3_CONFIG
from utils.log import log as logger

# ------------------------------------------------------------------------------------

def get_web3_config_by_chainid(chainid):
    assert chainid in [0, 11155111, 84532]
    web3_configs = json.loads(WEB3_CONFIG)
    for web3_client in web3_configs:
        if chainid>0:
            if web3_client['chain_id'] == chainid:
                return web3_client
        else:
            if web3_client['network'] == WEB3_NETWORK:
                return web3_client
    return web3_configs[0]

def get_web3_config_by_network(network=WEB3_NETWORK):
    assert network in ["Ethereum Sepolia", "Base Sepolia"]
    web3_configs: list = json.loads(WEB3_CONFIG)
    for web3_client in web3_configs:
        if web3_client['network'] == network:
            return web3_client
    return web3_configs[0]

# ------------------------------------------------------------------------------------