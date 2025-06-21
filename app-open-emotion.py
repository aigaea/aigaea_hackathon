#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import asyncio
import datetime
import json
import random
import sys
import time
from web3 import Web3
from datetime import datetime as dt

import pymysql

from config import DB_CONFIG, APP_CONFIG, WEB3_NETWORK, WEB3_WHITE_PRIKEY
from utils.cache import get_redis_data, set_redis_data, del_redis_data
from utils.web3_tools import get_web3_config_by_network
from utils.log import log as logger

"""
- Open the lottery or start the next round based on database parameters
"""

issue_index = 0

# ABI
contract_abi_emotion = [
        {
            "inputs": [],
            "name": "userProportion",
            "outputs": [
                { "internalType": "uint256", "name": "", "type": "uint256" }
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                { "internalType": "uint256", "name": "newUserProportion", "type": "uint256" }
            ],
            "name": "setProportion",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [
                { "internalType": "uint256", "name": "", "type": "uint256" }
            ],
            "name": "IssueReward",
            "outputs": [
                { "internalType": "uint256", "name": "", "type": "uint256" }
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "Issue",
            "outputs": [
                { "internalType": "uint256", "name": "", "type": "uint256" }
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                { "internalType": "uint256", "name": "", "type": "uint256" }
            ],
            "name": "IssueAddressNum",
            "outputs": [
                { "internalType": "uint256", "name": "", "type": "uint256" }
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                { "internalType": "uint256", "name": "", "type": "uint256" }
            ],
            "name": "IssueInformation",
            "outputs": [
                { "internalType": "uint256", "name": "duration", "type": "uint256" },
                { "internalType": "uint256", "name": "price", "type": "uint256" },
                { "internalType": "uint256", "name": "putmoney", "type": "uint256" }
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                { "internalType": "uint256", "name": "", "type": "uint256" }
            ],
            "name": "IssueEmotion",
            "outputs": [
                { "internalType": "uint256", "name": "", "type": "uint256" }
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                { "internalType": "uint256", "name": "_Issue", "type": "uint256" },
                { "internalType": "uint256", "name": "_num", "type": "uint256" }
            ],
            "name": "getIssueEmotionAddrslength",
            "outputs": [
                { "internalType": "uint256", "name": "", "type": "uint256" }
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
			"inputs": [],
			"name": "openVRFRandomEmotions",
			"outputs": [],
			"stateMutability": "nonpayable",
			"type": "function"
		},
        {
            "inputs": [],
            "name": "openEmotions",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [
                { "internalType": "uint256", "name": "_duration", "type": "uint256" },
                { "internalType": "uint256", "name": "_price", "type": "uint256" },
                { "internalType": "uint256", "name": "_putmoney", "type": "uint256" }
            ],
            "name": "openNewIssue",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        },
    ]


# ------------------------------------------------------------------------------------

def web3_is_connected_with_retry(web3_obj, max_retries=5, retry_interval=2):
    attempt = 0
    while attempt < max_retries:
        try:
            connected = web3_obj.is_connected()
            return connected
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            attempt += 1
            if attempt < max_retries:
                logger.debug(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                logger.error("Max retries reached. Failed to is_connected.")
                return 0

def send_transaction(web3_obj, transaction):
        try:
            logger.info(f"transaction: {transaction}")
            try:
                gas_limit = web3_obj.eth.estimate_gas(transaction)
            except Exception as e:
                logger.error(f"Failed to eth.estimate_gas: {str(e)}")
                gas_limit = 20000000
            logger.info(f"gas_limit: {gas_limit}")
            
            transaction.update({
                "gas": gas_limit,
            })
            logger.info(f"update transaction: {transaction}")
            # Transaction gas
            total_gas_cost = transaction['maxFeePerGas'] * gas_limit
            total_gas_eth = web3_obj.from_wei(total_gas_cost, 'ether')
            logger.info(f"Transaction gas: {total_gas_cost} wei / {total_gas_eth} ETH")
            
            signed_transaction = web3_obj.eth.account.sign_transaction(transaction, WEB3_WHITE_PRIKEY)
            logger.debug(f"Transaction signature: {signed_transaction}")
            
            try:
                if str(signed_transaction).find("raw_transaction") > 0:
                    tx_hash = web3_obj.eth.send_raw_transaction(signed_transaction.raw_transaction)
                elif str(signed_transaction).find("signed_transaction") > 0:
                    tx_hash = web3_obj.eth.send_raw_transaction(signed_transaction.raw_transaction)
                logger.info(f"Transaction sent - hash: {tx_hash.hex()}")
                
                receipt = web3_obj.eth.wait_for_transaction_receipt(tx_hash)
                logger.info(f"Transaction completed - receipt: {receipt}")
                tx_bytes = f"0x{tx_hash.hex()}"
                
                if receipt['status'] == 1:
                    logger.info(f"Transaction successful - hash: {tx_bytes}")
                    return True, {"tx_hash": tx_bytes}
                else:
                    logger.error(f"Transaction failed - hash: {tx_bytes}")
                    return False, {"tx_hash": tx_bytes}
            except ValueError as e:
                logger.info(f"Failed to transfer ValueError ETH : {str(e)}")
                try:
                    if e.args[0].get('message') in 'intrinsic gas too low':
                        result = False, {"tx_hash": tx_bytes, "msg": e.args[0].get('message')}
                    else:
                        result = False, {"tx_hash": tx_bytes, "msg": e.args[0].get('message'), "code": e.args[0].get('code')}
                except Exception as e:
                    result = False, {"tx_hash": tx_bytes, "msg": str(e)}
                return result
        except Exception as e:
            logger.error(f"Failed to eth.send_raw_transaction: {str(e)}")
            return False, {"tx_hash": "send_raw_transaction", "msg": str(e)}

# ------------------------------------------------------------------------------------

async def main_open_emotion():
    global issue_index
    logger.info(f"main_open_emotion start")
    while True:
        try:
            # MySQL database connection
            conn = pymysql.connect(
                host=DB_CONFIG['master'],
                port=DB_CONFIG['port'],
                user=DB_CONFIG['username'],
                passwd=DB_CONFIG['password'],
                db=DB_CONFIG['database'],
                charset='utf8mb4',
                autocommit=True,
            )
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            current_timestamp = int(time.time())
            logger.debug(f"current_timestamp: {current_timestamp}")

            ## Query maximum period_id from database
            check_query = """
                            SELECT 
                                period_id as id 
                            FROM gaea_emotions 
                            WHERE 
                                period_id > 0 
                            ORDER BY period_id DESC LIMIT 1
                          """
            values = ()
            cursor.execute(check_query, values)
            emotion_info = cursor.fetchone()
            logger.debug(f"mysql emotion_info: {emotion_info}")
            if emotion_info:
                max_period_id = emotion_info['id']
            else:
                max_period_id = 0
            if max_period_id == 0:
                raise Exception("The gaea_emotions table has no data")

            web3_config = get_web3_config_by_network(WEB3_NETWORK)
            logger.debug(f"web3_config: {web3_config}")
            config_chainid = web3_config['chain_id'] # chain_id
            if not config_chainid:
                raise Exception("Web3 chain_id not found")
            web3_rpc_url = web3_config['server'] # rpc
            if not web3_rpc_url:
                raise Exception("Web3 rpc not found")
            web3_obj = Web3(Web3.HTTPProvider(web3_rpc_url))
            # Connecting to the RPC Node
            while not web3_is_connected_with_retry(web3_obj):
                logger.error(f"Ooops! Failed to eth.is_connected.")
                time.sleep(10)

            # Whitelist address
            sender_address = web3_obj.eth.account.from_key(WEB3_WHITE_PRIKEY).address
            sender_balance = web3_obj.eth.get_balance(sender_address)
            logger.debug(f"white_address: {sender_address} balance: {web3_obj.from_wei(sender_balance, 'ether')} ETH")

            # emotion
            emotion_address = web3_config['emotion']
            emotion_contract_address = Web3.to_checksum_address(emotion_address)
            emotion_contract = web3_obj.eth.contract(address=emotion_contract_address, abi=contract_abi_emotion)
            if not (len(emotion_address) == 42 and emotion_address[:2] == '0x'): 
                logger.error(f"Invalid emotion_contract address - {emotion_address}")
                return {"code": 401, "success": False, "msg": "Invalid emotion_contract address"}
            logger.info(f"emotion_address: {emotion_address}")

            ## Get current period_id from smart contract
            current_period_id = emotion_contract.functions.Issue().call()
            logger.debug(f"current_period_id: {current_period_id}")
            if not isinstance(current_period_id, int) or current_period_id < 0:
                raise Exception("Invalid period_id from emotion_contract.functions.Issue().call()")
            
            if current_period_id > 0 and issue_index == current_period_id:
                logger.error(f"issue_index: {issue_index} == current_period_id: {current_period_id}, Please wait 600 Seconds")
                time.sleep(600)
                continue
            
            # Sync missing period data from contract to database
            if current_period_id > max_period_id+1:
                logger.info(f"current_period_id: {current_period_id} > max_period_id: {max_period_id}")
                for period_id in range(max_period_id+1, current_period_id):
                    # Update the parameters of this period
                    period_emotion = emotion_contract.functions.IssueEmotion(period_id).call()
                    logger.debug(f"period_emotion: {period_emotion}")
                    time.sleep(1)
                    if period_emotion == 0:
                        continue
                    period_average = emotion_contract.functions.IssueReward(period_id).call()
                    logger.debug(f"period_average: {period_average}")
                    time.sleep(1)
                    # Number of participants
                    period_total = emotion_contract.functions.IssueAddressNum(period_id).call()
                    logger.debug(f"period_total: {period_total}")
                    time.sleep(1)
                    period_info = emotion_contract.functions.IssueInformation(period_id).call()
                    logger.debug(f"period_info: {period_info}")
                    time.sleep(1)
                    end_timestamp = period_info[0]  # Current period end timestamp
                    period_price = period_info[1]    # Current price
                    period_putmoney = period_info[2]  # Current base position
                    period_proportion = emotion_contract.functions.userProportion().call()
                    logger.debug(f"period_proportion: {period_proportion}")
                    time.sleep(1)
                    period_reward = period_total * period_price * period_proportion / 100 + period_putmoney
                    logger.debug(f"period_reward: {period_reward}")

                    if current_timestamp < end_timestamp:
                        logger.info(f"period_id: {period_id} - Please wait {end_timestamp - current_timestamp} Seconds")
                        continue

                    # Number of emotional participants
                    emotion_positive = emotion_contract.functions.getIssueEmotionAddrslength(period_id, 1).call()
                    logger.debug(f"emotion_positive: {emotion_positive}")
                    time.sleep(1)
                    emotion_neutral = emotion_contract.functions.getIssueEmotionAddrslength(period_id, 2).call()
                    logger.debug(f"emotion_neutral: {emotion_neutral}")
                    time.sleep(1)
                    emotion_negative = emotion_contract.functions.getIssueEmotionAddrslength(period_id, 3).call()
                    logger.debug(f"emotion_negative: {emotion_negative}")
                    
                    # Insert emotions state 2
                    insert_query = """
                                    INSERT INTO gaea_emotions (period_id,period_putmoney,period_proportion,period_price,period_end,period_emotion,period_average,period_reward,period_total,emotion_positive,emotion_neutral,emotion_negative,status) 
                                    SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s 
                                    WHERE 
                                        NOT EXISTS (SELECT id FROM gaea_emotions WHERE period_id = %s)
                                    """
                                    
                    values = (period_id, period_putmoney, period_proportion, period_price,end_timestamp, period_emotion, int(period_average), int(period_reward), period_total, emotion_positive, emotion_neutral, emotion_negative, 2, period_id)
                    # logger.debug(f"insert_query: {insert_query} values: {values}")
                    cursor.execute(insert_query, values)
                    cursor.connection.commit()
                    logger.debug(f"insert gaea_emotions - status=2")
                continue

            # Current Information
            current_period_info = emotion_contract.functions.IssueInformation(current_period_id).call()
            logger.debug(f"current_period_info: {current_period_info}")
            time.sleep(1)
            end_timestamp = current_period_info[0]  # Current period end timestamp
            current_period_price = current_period_info[1]  # Current price
            current_period_putmoney = current_period_info[2]  # Current base position

            current_timestamp = int(time.time())
            logger.debug(f"current_timestamp: {current_timestamp}")
            # Check if current period has ended
            if current_timestamp < end_timestamp: ## Not yet finished, sleep end_timestamp+10 seconds
                # Number of participants
                current_period_total = emotion_contract.functions.IssueAddressNum(current_period_id).call()
                logger.debug(f"period_total: {current_period_total}")
                time.sleep(1)
                # Number of emotional participants
                current_emotion_positive = emotion_contract.functions.getIssueEmotionAddrslength(current_period_id, 1).call()
                logger.debug(f"emotion_positive: {current_emotion_positive}")
                time.sleep(1)
                current_emotion_neutral = emotion_contract.functions.getIssueEmotionAddrslength(current_period_id, 2).call()
                logger.debug(f"emotion_neutral: {current_emotion_neutral}")
                time.sleep(1)
                current_emotion_negative = emotion_contract.functions.getIssueEmotionAddrslength(current_period_id, 3).call()
                logger.debug(f"emotion_negative: {current_emotion_negative}")
                # Update emotions state 1
                update_query = """
                                UPDATE gaea_emotions 
                                SET 
                                    period_end=%s,
                                    period_putmoney=%s,
                                    period_price=%s,
                                    period_total=%s,
                                    emotion_positive=%s,
                                    emotion_neutral=%s,
                                    emotion_negative=%s,
                                    status=%s,
                                    updated_time=NOW()
                                WHERE 
                                    period_id = %s
                                """
                values = (end_timestamp, current_period_putmoney, current_period_price, current_period_total,current_emotion_positive,current_emotion_neutral,current_emotion_negative,1, current_period_id)
                # logger.debug(f"update_query: {update_query} values: {values}")
                cursor.execute(update_query, values)
                cursor.connection.commit()
                logger.success(f"update gaea_emotions - status=1 current_period_id: {current_period_id} period_end: {end_timestamp} period_price: {current_period_price}")

                calc_timestamp = end_timestamp - current_timestamp
                logger.info(f"The {current_period_id} period is in progress - Please wait {calc_timestamp} Seconds")
                time.sleep(calc_timestamp+10)
                continue
            else: ## Ended
                # Get the current Gas
                base_fee = web3_obj.eth.get_block('latest')['baseFeePerGas']
                priority_fee = web3_obj.eth.max_priority_fee
                max_fee = base_fee * 2 + priority_fee
                logger.debug(f"base_fee: {base_fee}, priority_fee: {priority_fee}, max_fee: {max_fee}")
                
                # current emotion
                current_emotion = emotion_contract.functions.IssueEmotion(current_period_id).call()
                logger.debug(f"current_emotion: {current_emotion}")
                time.sleep(1)
                # Get VRF random number
                if current_emotion == 0 and current_period_id>0:
                    ## Get VRF random number
                    transaction = emotion_contract.functions.openVRFRandomEmotions( ).build_transaction(
                        {
                            "chainId": config_chainid,
                            "from": sender_address,
                            "nonce": web3_obj.eth.get_transaction_count(sender_address),
                            "maxPriorityFeePerGas": priority_fee,
                            "maxFeePerGas": max_fee,
                            "gas": base_fee * priority_fee,
                        }
                    )
                    logger.debug(f"transaction: {transaction}")
                    
                    # send_transaction
                    tx_success, _ = send_transaction(web3_obj, transaction)
                    if tx_success == False:
                        logger.error(f"Ooops! Failed to send_transaction.")
                        time.sleep(60)
                        continue
                    logger.success(f"Get VRF emotion successfully! - current_emotion: {current_emotion}")
                    
                    time.sleep(60)
                
                # Proportion
                period_proportion = emotion_contract.functions.userProportion().call()
                logger.debug(f"period_proportion: {period_proportion}")
                time.sleep(1)
                next_proportion = period_proportion
                
                # Draw or start the next round
                if current_period_id < max_period_id: ## start the next round
                    check_query = """
                                    SELECT 
                                        period_duration as duration,
                                        period_price as price,
                                        period_putmoney as putmoney,
                                        period_proportion as proportion
                                    FROM gaea_emotions 
                                    WHERE 
                                        period_id = %s
                                    """
                    values = (current_period_id+1)
                    cursor.execute(check_query, values)
                    next_emotion_info = cursor.fetchone()
                    logger.debug(f"mysql next_emotion_info: {next_emotion_info}")
                    if next_emotion_info is None:
                        raise Exception(f"The {current_period_id+1} period is empty")
                    # Get the share ratio
                    next_proportion = int(next_emotion_info['proportion'])

                    ## Start the next round
                    duration = int(next_emotion_info['duration'])
                    price = int(next_emotion_info['price'])+random.randint(0,4)*10000 # price+0.04
                    putmoney = int(next_emotion_info['putmoney'])
                    
                    if duration >= 24*3600:
                        today_zero_timestamp = int(time.mktime(time.strptime(str(datetime.date.today()), '%Y-%m-%d')))
                        delay = current_timestamp - today_zero_timestamp
                        logger.debug(f"today_zero_timestamp delay: {delay}")
                        if delay >= 12*3600:
                            duration = duration - delay + 24*3600
                        else:
                            duration = duration - delay

                    logger.debug(f"sender_address: {sender_address}")
                    ## Start the next round
                    transaction = emotion_contract.functions.openNewIssue( duration, price, putmoney ).build_transaction(
                        {
                            "chainId": config_chainid,
                            "from": sender_address,
                            "nonce": web3_obj.eth.get_transaction_count(sender_address),
                            "maxPriorityFeePerGas": priority_fee,
                            "maxFeePerGas": max_fee,
                            "gas": base_fee * priority_fee,
                        }
                    )
                    logger.debug(f"transaction: {transaction}")
                else: ## Prize draw
                    if current_emotion > 0:
                        raise Exception(f"The {current_period_id} period has been announced")

                    logger.debug(f"sender_address: {sender_address}")
                    ## Prize draw
                    transaction = emotion_contract.functions.openEmotions( ).build_transaction(
                        {
                            "chainId": config_chainid,
                            "from": sender_address,
                            "nonce": web3_obj.eth.get_transaction_count(sender_address),
                            "maxPriorityFeePerGas": priority_fee,
                            "maxFeePerGas": max_fee,
                            "gas": base_fee * priority_fee,
                        }
                    )
                    logger.debug(f"transaction: {transaction}")

                # send_transaction
                tx_success, _ = send_transaction(web3_obj, transaction)
                if tx_success == False:
                    logger.error(f"Ooops! Failed to send_transaction. Try again in 600 seconds")
                    time.sleep(600)
                    continue
                logger.success(f"The transaction was send successfully! - transaction: {transaction}")

                if current_period_id < max_period_id:
                    # Update emotions state 1
                    update_query = """
                                    UPDATE gaea_emotions 
                                    SET 
                                        period_start=%s,
                                        status=%s,
                                        updated_time=NOW() 
                                    WHERE 
                                        period_id = %s
                                    """
                    values = (current_timestamp, 1, current_period_id+1)
                    # logger.debug(f"update_query: {update_query} values: {values}")
                    cursor.execute(update_query, values)
                    cursor.connection.commit()
                    logger.success(f"update gaea_emotions - status=1 next_period_id: {current_period_id+1}")
                time.sleep(10)

                # Has the share ratio changed?
                if next_proportion != int(period_proportion): ## Modify the share ratio
                    transaction = emotion_contract.functions.setProportion( next_proportion ).build_transaction(
                        {
                            "chainId": config_chainid,
                            "from": sender_address,
                            "nonce": web3_obj.eth.get_transaction_count(sender_address),
                            "maxPriorityFeePerGas": priority_fee,
                            "maxFeePerGas": max_fee,
                            "gas": base_fee * priority_fee,
                        }
                    )
                    logger.debug(f"transaction: {transaction}")

                    # send_transaction
                    tx_success, _ = send_transaction(web3_obj, transaction)
                    if tx_success == False:
                        logger.error(f"Ooops! Failed to send_transaction.")
                        time.sleep(60)
                        continue
                    logger.success(f"The proportion was modified successfully! - next_proportion: {next_proportion}")
                    
                    time.sleep(10)

                ## Update the parameters of this period
                current_emotion = emotion_contract.functions.IssueEmotion(current_period_id).call()
                logger.debug(f"current_emotion: {current_emotion}")
                time.sleep(1)
                current_period_average = emotion_contract.functions.IssueReward(current_period_id).call()
                logger.debug(f"period_average: {current_period_average}")
                time.sleep(1)
                # Number of participants
                current_period_total = emotion_contract.functions.IssueAddressNum(current_period_id).call()
                logger.debug(f"period_total: {current_period_total}")
                time.sleep(1)
                current_period_reward = current_period_total * current_period_price * period_proportion / 100 + current_period_putmoney
                logger.debug(f"current_period_reward: {current_period_reward}")
                # Number of emotional participants
                current_emotion_positive = emotion_contract.functions.getIssueEmotionAddrslength(current_period_id, 1).call()
                logger.debug(f"emotion_positive: {current_emotion_positive}")
                time.sleep(1)
                current_emotion_neutral = emotion_contract.functions.getIssueEmotionAddrslength(current_period_id, 2).call()
                logger.debug(f"emotion_neutral: {current_emotion_neutral}")
                time.sleep(1)
                current_emotion_negative = emotion_contract.functions.getIssueEmotionAddrslength(current_period_id, 3).call()
                logger.debug(f"emotion_negative: {current_emotion_negative}")

                # Update emotions state 2
                update_query = """
                                UPDATE gaea_emotions 
                                SET 
                                    period_end=%s,
                                    period_putmoney=%s,
                                    period_price=%s,
                                    period_emotion=%s,
                                    period_average=%s,
                                    period_reward=%s,
                                    period_total=%s,
                                    emotion_positive=%s,
                                    emotion_neutral=%s,
                                    emotion_negative=%s,
                                    status=%s,
                                    updated_time=NOW() 
                                WHERE 
                                    period_id = %s
                                """
                values = (end_timestamp, current_period_putmoney, current_period_price, current_emotion, int(current_period_average), int(current_period_reward), current_period_total, current_emotion_positive, current_emotion_neutral, current_emotion_negative, 2, current_period_id)
                # logger.debug(f"update_query: {update_query} values: {values}")
                cursor.execute(update_query, values)
                cursor.connection.commit()
                logger.success(f"update gaea_emotions - status=2 current_period_id: {current_period_id} reward: {current_period_reward} average: {current_period_average}")

                await del_redis_data(True, f"hackathon:period:{config_chainid}:current")
                await del_redis_data(True, f"hackathon:period:{config_chainid}:{current_period_id}:list")
                
                issue_index = current_period_id

        except Exception as e:
            logger.error(f"main_open_emotion error: {e} , Please wait 600 Seconds")
            time.sleep(600)
    logger.info(f"main_open_emotion end")


if __name__ == "__main__":
    # argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', type=bool, default=False, action=argparse.BooleanOptionalAction)
    args = parser.parse_args()
    run_debug = bool(args.debug)

    # log level
    log_level = "DEBUG" if run_debug else "INFO"
    logger.remove()
    logger.add(sys.stdout, level=log_level)

    asyncio.run(main_open_emotion())

