import os
import sys
import json
import time
import random
import argparse
import asyncio
import pymysql
import requests
import threading
import concurrent.futures
from web3 import Web3
from loguru import logger
from datetime import datetime as dt
from dbutils.pooled_db import PooledDB

from utils.web3_tools import get_web3_config_by_chainid
from config import DB_CONFIG

"""
- training event monitoring
"""

hash_file = 'hash_emotion'
hash_index = 0

# ABI
contract_abi_emotion = [
        {
            "anonymous": False,
            "inputs": [
                { "indexed": False, "internalType": "uint256", "name": "", "type": "uint256" },
                { "indexed": False, "internalType": "uint8", "name": "", "type": "uint8" },
                { "indexed": False, "internalType": "address", "name": "", "type": "address" }
            ],
            "name": "Emotions",
            "type": "event"
        },
		{
			"anonymous": False,
			"inputs": [
				{"indexed": True,"internalType": "uint256","name": "issue","type": "uint256"},
				{"indexed": False,"internalType": "uint256","name": "requestId","type": "uint256"}
			],
			"name": "OpenVrfInitiated",
			"type": "event"
		},
        {
			"anonymous": False,
			"inputs": [
				{"indexed": True,"internalType": "uint256","name": "issue","type": "uint256"},
				{"indexed": False,"internalType": "uint256","name": "requestId","type": "uint256"},
				{"indexed": False,"internalType": "uint256","name": "emotionResult","type": "uint256"}
			],
			"name": "OpenVrfCompleted",
			"type": "event"
		},
		{
			"anonymous": False,
			"inputs": [
				{"indexed": True,"internalType": "uint256","name": "issue","type": "uint256"},
				{"indexed": False,"internalType": "uint256","name": "usertotal","type": "uint256"},
				{"indexed": False,"internalType": "uint256","name": "useraverage","type": "uint256"}
			],
			"name": "OpenEmotions",
			"type": "event"
		}
    ]

# Creating a Connection Pool
pool = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=2,
    maxcached=5,
    maxshared=3,
    blocking=True,
    ping=2,
    host=DB_CONFIG['master'],
    port=DB_CONFIG['port'],
    user=DB_CONFIG['username'],
    passwd=DB_CONFIG['password'],
    db=DB_CONFIG['database'],
    charset='utf8mb4',
)

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

def get_block_number_with_retry(web3_obj, max_retries=5, retry_interval=2):
    attempt = 0
    while attempt < max_retries:
        try:
            current_block = web3_obj.eth.block_number
            current_block -= 3  # Delay 6 seconds, 3 blocks
            return current_block
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            attempt += 1
            if attempt < max_retries:
                logger.debug(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                logger.error("Max retries reached. Failed to eth.block_number.")
                return 0

def get_block_with_retry(web3_obj, block_number, max_retries=5, retry_interval=2):
    attempt = 0
    while attempt < max_retries:
        try:
            block = web3_obj.eth.get_block(block_number, full_transactions=True)
            return block
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            attempt += 1
            if attempt < max_retries:
                logger.debug(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                logger.error("Max retries reached. Failed to eth.get_block.")
                return None

def get_transaction_receipt_with_retry(web3_obj, tx_hash, max_retries=5, retry_interval=2):
    attempt = 0
    while attempt < max_retries:
        try:
            tx_receipt = web3_obj.eth.get_transaction_receipt(tx_hash)
            return tx_receipt
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            attempt += 1
            if attempt < max_retries:
                logger.debug(f"Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                logger.error("Max retries reached. Failed to eth.get_transaction_receipt.")
                return None

def get_event_logs_with_retry(contract_event, from_block, to_block, max_retries=5, retry_interval=2):
    attempt = 0
    while attempt < max_retries:
        try:
            return contract_event.get_logs(from_block=from_block, to_block=to_block)
        except Exception as e:
            logger.error(f"Event logs attempt {attempt+1} failed: {str(e)}")
            attempt += 1
            time.sleep(retry_interval)
    logger.error("Max retries reached for event logs query")
    return []

# ------------------------------------------------------------------------------------

# Monitor blocks and parse related transactions into the database
def listen_events_start(web3_config, hash_index):
    global hash_file

    config_network = web3_config['network'] # network
    config_chainid = web3_config['chain_id'] # chain_id
    if not config_chainid:
        raise Exception("Web3 chain_id not found")

    web3_rpc_url = web3_config['server'] # rpc
    if not web3_rpc_url:
        raise Exception("Web3 rpc not found")
    web3_obj = Web3(Web3.HTTPProvider(web3_rpc_url))
    # Connecting to the RPC Node
    while not web3_is_connected_with_retry(web3_obj):
        logger.error(f"Ooops! Failed to eth.is_connected. {web3_rpc_url}")
        time.sleep(10)

    retry_interval = web3_config.get('interval', 10) * 10
    
    # emotion
    emotion_address = web3_config['emotion']
    emotion_contract_address = Web3.to_checksum_address(emotion_address)
    emotion_contract = web3_obj.eth.contract(address=emotion_contract_address, abi=contract_abi_emotion)
    if not (len(emotion_address) == 42 and emotion_address[:2] == '0x'): 
        logger.error(f"Invalid emotion_contract address - {emotion_address}")
        return {"code": 401, "success": False, "msg": "Invalid emotion_contract address"}
    logger.info(f"emotion_address: {emotion_address} config_chainid: {config_chainid}")

    MAX_BLOCK_RANGE = 5000
    while True:
        try:
            current_block = get_block_number_with_retry(web3_obj)
            logger.info(f"hash_index: {hash_index} current_block: {current_block} | calc_block: {current_block-hash_index} start")
            if current_block == 0:
                logger.error(f"Ooops! Failed to eth.block_number.")
                time.sleep(retry_interval)
                continue
            block_diff = current_block - hash_index
            if block_diff <= 0:
                logger.error(f"Ooops! Current block behind index: {block_diff}")
                time.sleep(retry_interval)
                continue
            to_block = min(current_block, hash_index + MAX_BLOCK_RANGE)
            logger.debug(f"Processing blocks: {hash_index} to {to_block} (diff: {to_block - hash_index})")

            events = emotion_contract.events.Emotions.get_logs(from_block=web3_obj.to_hex(hash_index), to_block=to_block)
            # events = get_event_logs_with_retry(
            #     emotion_contract.events.Emotions,
            #     from_block=hash_index,
            #     to_block=to_block,
            # )
            for event in events:
                logger.info(f"Emotions event: {event}")
                block_number = int(event.blockNumber)
                logger.info(f"block_number: {block_number}")
                
                block = get_block_with_retry(web3_obj, block_number)
                if block is None:
                    raise Exception("Ooops! Failed to eth.get_block.")
                
                # Parsing block time
                block_timestamp = block.timestamp
                logger.debug(f"block_timestamp: {block_timestamp}")
                block_time = dt.fromtimestamp(block_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                logger.debug(f"block_time: {block_time}")
                
                tx_hash = f"0x{event.transactionHash.hex()}"
                logger.info(f"tx_hash: {tx_hash}")

                # Parsing hash status
                tx_receipt = get_transaction_receipt_with_retry(web3_obj, tx_hash)
                if tx_receipt is None:
                    logger.error(f"Ooops! Transaction not found | tx_hash: {tx_hash}")
                    continue
                else:
                    logger.debug(f"transaction is {tx_receipt}")
                    if tx_receipt['status'] != 1:
                        logger.error(f"Ooops! Transaction failed | tx: {tx_receipt['from']}")
                        continue
                    if len(tx_receipt.get('logs')) == 0:
                        logger.error(f"Ooops! tx_receipt logs not found | tx_hash: {tx_hash}")
                        continue

                tx_from = tx_receipt['from'].lower()
                tx_to = tx_receipt['to'].lower()
                logger.debug(f"tx_from: {tx_from} tx_to: {tx_to}")
                if emotion_address.lower() != tx_to:
                    logger.error(f"Ooops! emotion_address not found | tx_hash: {tx_hash}")
                    continue
                logger.debug(f"tx_from: {tx_from} tx_to: {tx_to}")

                money = Web3.to_hex(tx_receipt.get('logs')[0].get('data'))
                payee = Web3.to_hex(tx_receipt.get('logs')[0].get('topics')[2])
                cool_amount = int(money, 16)             # Cold wallet amount
                cool_address = '0x'+payee[26:66].lower() # Cold wallet address
                emotion_data = Web3.to_hex(tx_receipt.get('logs')[1].get('data'))
                period_id = int(emotion_data[2:66], 16)        # Current ID
                period_emotion = int(emotion_data[90:130],16)  # Current emotions
                tx_from = '0x'+emotion_data[154:194].lower()   # from
                logger.debug(f"tx_from: {tx_from} tx_to: {tx_to}")
                logger.debug(f"cool_address: {cool_address} cool_amount: {cool_amount}  period_id: {period_id} period_emotion: {period_emotion}")

                status=1
                note=''
                address=tx_from.lower()
                
                conn = pool.connection()
                cursor = conn.cursor(pymysql.cursors.DictCursor)

                # Emotion storage
                insert_query = """
                                INSERT INTO hack_emotion_onchain 
                                    (address, tx_chainid, tx_blockid, tx_hash, tx_date, cool_address, cool_amount, period_id, period_emotion, status, note) 
                                SELECT 
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                WHERE 
                                    NOT EXISTS (SELECT id FROM hack_emotion_onchain WHERE tx_hash = %s)
                                """
                values = (address, config_chainid, block_number, tx_hash, block_time, cool_address, cool_amount, period_id, period_emotion, status, note, tx_hash)
                # logger.debug(f"insert_query: {insert_query} values: {values}")
                cursor.execute(insert_query, values)
                cursor.connection.commit()
                logger.debug(f"insert hack_emotion_onchain success!")

                check_query = """
                                SELECT id
                                FROM hack_emotion_onchain 
                                WHERE 
                                    tx_hash = %s AND status=1
                                """
                values = (tx_hash)
                cursor.execute(check_query, values)
                one_transaction = cursor.fetchone()
                logger.debug(f"one_transaction: {one_transaction}")

                if one_transaction: # Training elimination
                    trainid = one_transaction['id']
                    today = block_time[:10]
                    # Training elimination
                    if config_chainid == 11155111:
                        trainnetwork = "eth"
                    elif config_chainid == 84532:
                        trainnetwork = "base"
                    elif config_chainid == 43113:
                        trainnetwork = "avax"
                    elif config_chainid == 97:
                        trainnetwork = "bsc"
                    else:
                        trainnetwork = "eth"
                    check_query = f"""
                                    SELECT id 
                                    FROM hack_emotion_training 
                                    WHERE trainid_{trainnetwork} = %s
                                    """
                    values = (trainid)
                    # print(f"check_query: {check_query}, values: {values}")
                    cursor.execute(check_query, values)
                    exist_deeptraining = cursor.fetchall()
                    logger.debug(f"deeptraining exist_deeptraining: {len(exist_deeptraining)}")
                    if not exist_deeptraining:
                        check_query = f"""
                                        SELECT id 
                                        FROM hack_emotion_training 
                                        WHERE address = %s and status = 1 and date = %s and trainid_{trainnetwork} = 0
                                        """
                        values = (address, today)
                        # print(f"check_query: {check_query}, values: {values}")
                        cursor.execute(check_query, values)
                        exist_training = cursor.fetchone()
                        logger.debug(f"deeptraining exist_training: {exist_training}")
                        if not exist_training:
                            logger.error(f"No data training hack_emotion_training not found! one_transaction: {one_transaction}")
                        else:
                            # Update deep training status
                            update_query = f"""
                                            UPDATE hack_emotion_training 
                                            SET 
                                                trainid_{trainnetwork}=%s,
                                                updated_time=NOW() 
                                            WHERE id = %s
                                            """
                            values = (trainid, exist_training['id'])
                            cursor.execute(update_query, values)
                            cursor.connection.commit()
                            logger.success(f"update hack_emotion_training success! trainid: {trainid} id: {exist_training['id']}")
                        
                        # Start emotional deep training
                        insert_query = """
                                        INSERT INTO hack_emotion_training
                                            (address, detail, status, date) 
                                        SELECT
                                            %s, (SELECT detail FROM hack_emotion_training WHERE address = %s and status = 1 and date = %s), %s, %s
                                        WHERE 
                                            EXISTS (SELECT id FROM hack_emotion_training WHERE address = %s and status = 1 and date = %s)
                                            AND NOT EXISTS (SELECT id FROM hack_emotion_training WHERE address = %s and status = 2 and date = %s)
                                        """
                        values = (address, address, today, 2, today, address, today, address, today)
                        cursor.execute(insert_query, values)
                        cursor.connection.commit()
                        logger.success(f"insert hack_emotion_training success! address: {address} status: 2")

                        randuuid = random.randint(1, 99999)
                        # Update signin status
                        update_query = """
                                        UPDATE hack_emotion_onchain 
                                        SET 
                                            period_uuid=%s,
                                            updated_time=NOW()
                                        WHERE
                                            id = %s
                                        """
                        values = (randuuid, trainid)
                        cursor.execute(update_query, values)
                        cursor.connection.commit()
                        logger.success(f"update hack_emotion_onchain success! one_transaction: {one_transaction}")
                        # Update current period's data
                        if period_emotion in [1, 2, 3]:
                            emotion_columns = {
                                1: 'emotion_positive',
                                2: 'emotion_neutral',
                                3: 'emotion_negative'
                            }
                            update_query = f"""
                                            UPDATE hack_emotions 
                                            SET
                                                period_total = period_total + 1,
                                                {emotion_columns[period_emotion]} = {emotion_columns[period_emotion]} + 1,
                                                updated_time = NOW() 
                                            WHERE period_id = %s AND status = 1
                                            """
                            values = (period_id,)
                            cursor.execute(update_query, values)
                            cursor.connection.commit()
                            logger.success(f"update hack_emotions - period_total+1")
                        else:
                            logger.error(f"Invalid period_emotion value: {period_emotion}")
                    else:
                        logger.success(f"Already deeptraining - exist_deeptraining: {len(exist_deeptraining)}")

            events = emotion_contract.events.OpenVrfInitiated.get_logs(from_block=web3_obj.to_hex(hash_index), to_block=current_block)
            for event in events:
                logger.info(f"OpenVrfInitiated event: {event}")
            
            events = emotion_contract.events.OpenVrfCompleted.get_logs(from_block=web3_obj.to_hex(hash_index), to_block=current_block)
            for event in events:
                logger.info(f"OpenVrfCompleted event: {event}")
            
            events = emotion_contract.events.OpenEmotions.get_logs(from_block=web3_obj.to_hex(hash_index), to_block=current_block)
            for event in events:
                logger.info(f"OpenEmotions event: {event}")
            
            logger.info(f"all items update complete. current_block: {current_block}")

            with open(hash_file, "w", encoding="utf-8") as f:
                f.write(str(current_block))
            hash_index = current_block+1

            time.sleep(retry_interval)
        except Exception as e:
            logger.error(f"listen_contract_event error: {e} , Please wait 600 Seconds")
            time.sleep(600)
            continue

async def listen_events(chainid):
    global hash_file
    global hash_index

    web3_config = get_web3_config_by_chainid(chainid)
    logger.debug(f"web3_config: {web3_config}")

    config_chainid = web3_config['chain_id'] # chain_id
    if not config_chainid:
        raise Exception("Web3 chain_id not found")

    hash_file=f"{config_chainid}_emotion"

    web3_rpc_url = web3_config['server'] # rpc
    if not web3_rpc_url:
        raise Exception("Web3 rpc not found")
    web3_obj = Web3(Web3.HTTPProvider(web3_rpc_url))
    while not web3_is_connected_with_retry(web3_obj):
        logger.debug(f"Ooops! Failed to eth.is_connected. {web3_rpc_url}")
        time.sleep(5)

    current_block=0
    while current_block == 0:
        current_block = get_block_number_with_retry(web3_obj)
        time.sleep(5)
    print(f"current_block: {current_block}")

    if not os.path.exists(hash_file):
        with open(hash_file, "w", encoding="utf-8") as f:
            f.write(str(current_block))
        hash_index = current_block
    else:
        with open(hash_file, "r", encoding="utf-8") as f:
            hash_index_str = f.read()
        if not hash_index_str:
            hash_index = current_block
        else:
            hash_index = int(hash_index_str)
    print(f"hash_index: {hash_index}")
    
    if current_block - hash_index > 100:
        logger.error(f"Warning, block height difference. - clac_block: {current_block - hash_index}")

    listen_events_start(web3_config, hash_index)


if __name__ == '__main__':
    # argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', type=bool, default=False, action=argparse.BooleanOptionalAction)
    parser.add_argument('-l', '--log', type=str, default="warn")
    parser.add_argument('-c', '--chainid', type=int, default=84532)
    args = parser.parse_args()
    run_debug = bool(args.debug)
    run_log = str(args.log.lower())
    run_chainid = int(args.chainid)

    # log level
    if run_debug:
        log_level = "DEBUG"
    else:
        if run_log == "debug":
            log_level = "DEBUG"
        elif run_log == "info":
            log_level = "INFO"
        elif run_log == "warn":
            log_level = "WARNING"
        elif run_log == "error":
            log_level = "ERROR"
        else:
            log_level = "WARNING"
    logger.remove()
    logger.add(sys.stdout, level=log_level)

    asyncio.run(listen_events(run_chainid))
