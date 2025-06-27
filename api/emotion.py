import hashlib
import json
import random
import re
import string
import time
import asyncio
import requests
import datetime
from datetime import datetime as dt
from typing import Dict
from web3 import Web3
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field

from utils.cache import get_redis_data, set_redis_data, del_redis_data
from utils.database import get_db, get_db_slave
from utils.web3_tools import get_web3_config_by_chainid
from utils.security import get_current_address
from utils.log import log as logger
from config import WEB3_NETWORK, WEB3_CONFIG

router = APIRouter()


## emotion

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
        }
    ]

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


@router.get("/web3_config")
async def godhood_web3_config():
    web3_config = await get_redis_data(False, f"hackathon:web3:config")
    if not web3_config:
        configs: list = json.loads(WEB3_CONFIG)
        # logger.debug(f"configs: {configs}")
        # configs = [config for config in configs if WEB3_NETWORK in config['network']]
        logger.debug(f"configs: {configs}")
        for config in configs:
            del config['server']
            del config['gas']
            del config['white_prikey']
            del config['interval']
        web3_config = {
            "network": WEB3_NETWORK,
            "config": configs,
        }
        await set_redis_data(False, f"hackathon:web3:config", web3_config, ex=86400)
    logger.debug(web3_config)
    return {"code": 200, "success": True, "msg": "Success", "data": web3_config}


class EmotionRequest(BaseModel):
    chain_id: int = Field(default=0, description="chainid")
@router.post("/period")
async def emotion_period(post_request: EmotionRequest, address: Dict = Depends(get_current_address), cursorSlave=Depends(get_db_slave)):
    """period info"""
    logger.info(f"POST /api/emotion/period - {address}")
    if cursorSlave is None:
        logger.error(f"/api/emotion/period - {address} cursorSlave: None")
        return {"code": 500, "success": False, "msg": "cursor error"}

    try:
        current_timestamp = int(time.time())
        logger.debug(f"current_timestamp: {current_timestamp}")

        chain_id = post_request.chain_id
        web3_config = get_web3_config_by_chainid(chain_id)
        logger.debug(f"web3_config: {web3_config}")
        if not web3_config:
            raise Exception("Web3 config not found")
        web3_rpc_url = web3_config['server'] # rpc
        if not web3_rpc_url:
            raise Exception("Web3 rpc not found")
        config_chainid = web3_config['chain_id'] # chain_id
        if not config_chainid:
            raise Exception("Web3 chain_id not found")
        if chain_id > 0 and config_chainid != chain_id:
            raise Exception("Web3 chainid does not match")
        else:
            chain_id = config_chainid
        
        # period_info
        current_period_info = await get_redis_data(True, f"hackathon:period:{chain_id}:current")
        logger.debug(f"redis current_period_info: {current_period_info}")
        if not current_period_info:
            # period_id
            check_query = """
                            SELECT
                                period_id 
                            FROM hack_emotions 
                            WHERE 
                                chain_id=%s AND `status`=1 
                            ORDER BY id DESC
                            LIMIT 1
                            """
            values = (chain_id,)
            await cursorSlave.execute(check_query, values)
            period_info = await cursorSlave.fetchone()
            logger.debug(f"mysql period_info: {period_info}")
            period_id = period_info['period_id'] if period_info else 0
            
            check_query = """
                            SELECT 
                                e1.period_id AS current_period_id,
                                e1.period_end AS current_period_end,
                                e1.period_duration AS current_period_duration,
                                e1.period_price AS current_period_price,
                                e1.period_putmoney AS current_period_putmoney,
                                e1.period_proportion AS current_period_proportion,
                                e1.period_reward AS current_period_reward,
                                e1.period_total AS current_period_total,
                                e1.status AS current_status,
                                e2.period_emotion AS last_period_emotion,
                                e2.period_average AS last_period_average
                            FROM 
                                hack_emotions e1
                            LEFT JOIN 
                                hack_emotions e2 ON e1.period_id - 1 = e2.period_id AND e2.chain_id=e1.chain_id
                            WHERE 
                                e1.chain_id=%s AND e1.status=1
                            """
            values = (chain_id,)
            await cursorSlave.execute(check_query, values)
            combined_info = await cursorSlave.fetchone()
            logger.debug(f"mysql combined_info: {combined_info}")
            if combined_info and period_id == combined_info['current_period_id']:
                current_period_info = {
                    "id": combined_info['current_period_id'],
                    "total": combined_info['current_period_total'],
                    "price": combined_info['current_period_price'],
                    "putmoney": combined_info['current_period_putmoney'],
                    "proportion": combined_info['current_period_proportion'],
                    "duration": combined_info['current_period_duration'],
                    "reward": int(combined_info['current_period_reward']),
                    "timestamp": combined_info['current_period_end'],
                    "last_emotion": combined_info['last_period_emotion'] or 0,
                    "last_average": combined_info['last_period_average'] or 0,
                    "status": combined_info['current_status'],
                }
                logger.debug(f"mysql current_period_info: {current_period_info}")
                await set_redis_data(True, f"hackathon:period:{chain_id}:current", value=json.dumps(current_period_info), ex=60)
            else:
                web3_obj = Web3(Web3.HTTPProvider(web3_rpc_url))
                # Connecting to the RPC Node
                while not web3_is_connected_with_retry(web3_obj):
                    logger.error(f"Ooops! Failed to eth.is_connected. {web3_rpc_url}")
                    time.sleep(10)
                logger.debug(f"web3_rpc_url: '{web3_rpc_url}' {type(web3_rpc_url)}")
                
                # emotion
                emotion_address = web3_config['emotion']
                if not (len(emotion_address) == 42 and emotion_address[:2] == '0x'): 
                    logger.error(f"Invalid emotion_contract address - {address}")
                    return {"code": 401, "success": False, "msg": "Invalid emotion_contract address"}
                # emotion contract
                emotion_contract_address = Web3.to_checksum_address(emotion_address)
                emotion_contract = web3_obj.eth.contract(address=emotion_contract_address, abi=contract_abi_emotion)
                
                period_id = emotion_contract.functions.Issue().call()
                logger.debug(f"period_id: {period_id}")
                time.sleep(0.5)
                period_total = emotion_contract.functions.IssueAddressNum(period_id).call()
                logger.debug(f"period_total: {period_total}")
                time.sleep(0.5)
                period_info = emotion_contract.functions.IssueInformation(period_id).call()
                logger.debug(f"period_info: {period_info}")
                time.sleep(0.5)
                end_timestamp = period_info[0]
                period_price = period_info[1]
                period_putmoney = period_info[2]
                period_proportion = emotion_contract.functions.userProportion().call()
                logger.debug(f"period_proportion: {period_proportion}")
                time.sleep(0.5)
                period_reward = period_total * period_price * period_proportion / 100 + period_putmoney
                logger.debug(f"period_reward: {period_reward}")
                if period_id>1:
                    last_emotion = emotion_contract.functions.IssueEmotion(period_id-1).call()
                    logger.debug(f"last_emotion: {last_emotion}")
                    time.sleep(0.5)
                    last_average = emotion_contract.functions.IssueReward(period_id-1).call()
                    logger.debug(f"last_average: {last_average}")
                else:
                    last_emotion = 0
                    last_average = 0
                
                check_query = """
                                SELECT 
                                    period_id, 
                                    period_duration 
                                FROM hack_emotions 
                                WHERE 
                                    period_id IN (%s, %s)
                                """
                values = (period_id, period_id - 1)
                await cursorSlave.execute(check_query, values)
                emotion_info_list = await cursorSlave.fetchall()
                logger.debug(f"mysql emotion_info_list: {emotion_info_list}")
                period_duration = 0
                for emotion_info in emotion_info_list:
                    if emotion_info['period_id'] == period_id:
                        period_duration = emotion_info['period_duration']
                
                if period_duration == 0:
                    period_duration = 172800
                
                calc_timestamp=current_timestamp-end_timestamp
                current_period_info = {
                    "id": period_id,
                    "total": period_total,
                    "price": period_price,
                    "putmoney": period_putmoney,
                    "proportion": period_proportion,
                    "duration": period_duration,
                    "reward": int(period_reward),
                    "timestamp": end_timestamp,
                    "last_emotion": last_emotion,
                    "last_average": last_average,
                    "status": 2 if calc_timestamp>0 else 1,
                }
                logger.debug(f"contract current_period_info: {current_period_info}")
                logger.debug(f"current: {dt.fromtimestamp(current_timestamp)} end: {dt.fromtimestamp(end_timestamp)} calc: {calc_timestamp}")
                await set_redis_data(True, f"hackathon:period:{chain_id}:current", value=json.dumps(current_period_info), ex=60)

        if current_period_info is None:
            return {
                "code": 200, 
                "success": True, 
                "msg": "success", 
                "data": current_period_info,
            }
        
        current_period_id = current_period_info['id']
        current_period_id = current_period_id if current_period_info['status'] != 2 else current_period_id + 1
        logger.debug(f"current_period_id: {current_period_id}")

        # User emotion
        last_emotion_list = await get_redis_data(False, f"hackathon:period:{chain_id}:{current_period_id}:{address}:last")
        logger.debug(f"redis last_emotion_list: {last_emotion_list}")
        if last_emotion_list is None:
            check_query = """
                    SELECT DISTINCT 
                        period_id as id, 
                        period_emotion as emotion, 
                        period_uuid as uuid 
                    FROM hack_emotion_onchain 
                    WHERE 
                        address = %s 
                        AND status = 1 
                        AND period_id >= %s 
                    ORDER BY period_id DESC 
                    LIMIT 2
                    """
            values = (address,current_period_id-1)
            # print(f"check_query: {check_query}, values: {values}")
            await cursorSlave.execute(check_query, values)
            last_emotion_list = await cursorSlave.fetchall()
            logger.debug(f"mysql last_emotion_list: {last_emotion_list}")
            if last_emotion_list:
                await set_redis_data(False, f"hackathon:period:{chain_id}:{current_period_id}:{address}:last", value=json.dumps(last_emotion_list), ex=600)
        
        # user_emotion
        user_period_info = []
        for period_id in range(current_period_id-1, current_period_id+1):
            logger.debug(f"period_id: {period_id}")
            unexist_mark = True
            if last_emotion_list:
                for last_emotion in last_emotion_list:
                    if last_emotion['id'] == period_id:
                        unexist_mark = False
                        user_period_info.append({ "id": period_id, "emotion": last_emotion['emotion'], "uuid": last_emotion['uuid']})
            if unexist_mark:
                user_period_info.append({ "id": period_id, "emotion": 0, "uuid": 0})
        user_period_info.sort(key=lambda x: x['id'], reverse=False)
        logger.debug(f"user_period_info: {user_period_info}")
        current_period_info['user_emotion'] = user_period_info

        return {
            "code": 200, 
            "success": True, 
            "msg": "success", 
            "data": current_period_info,
        }
    except Exception as e:
        logger.error(f"/api/emotion/period - {address} except ERROR: {str(e)}")
        return {"code": 500, "success": False, "msg": "Server error"}

@router.post("/period-history")
async def emotion_period_history(post_request: EmotionRequest, address: Dict = Depends(get_current_address), cursor=Depends(get_db), cursorSlave=Depends(get_db_slave)):
    """period history"""
    logger.info(f"POST /api/emotion/history - {address}")
    if cursor is None:
        logger.error(f"/api/emotion/history - {address} cursor: None")
        return {"code": 500, "success": False, "msg": "cursor error"}

    try:
        current_timestamp = int(time.time())
        logger.debug(f"current_timestamp: {current_timestamp}")

        chain_id = post_request.chain_id
        web3_config = get_web3_config_by_chainid(chain_id)
        logger.debug(f"web3_config: {web3_config}")
        if not web3_config:
            raise Exception("Web3 config not found")
        web3_rpc_url = web3_config['server'] # rpc
        if not web3_rpc_url:
            raise Exception("Web3 rpc not found")
        config_chainid = web3_config['chain_id'] # chain_id
        if not config_chainid:
            raise Exception("Web3 chain_id not found")
        if chain_id > 0 and config_chainid != chain_id:
            raise Exception("Web3 chainid does not match")
        else:
            chain_id = config_chainid
        
        # Period info
        current_period_info = await get_redis_data(True, f"hackathon:period:{chain_id}:current")
        logger.debug(f"redis current_period_info: {current_period_info}")
        if not current_period_info:
            # period_id
            check_query = """
                            SELECT 
                                period_id 
                            FROM hack_emotions 
                            WHERE 
                                `status`=1 
                            ORDER BY id DESC
                            LIMIT 1
                            """
            await cursorSlave.execute(check_query)
            period_info = await cursorSlave.fetchone()
            logger.debug(f"mysql period_info: {period_info}")
            period_id = period_info['period_id'] if period_info else 0
            
            check_query = """
                            SELECT 
                                e1.period_id AS current_period_id,
                                e1.period_end AS current_period_end,
                                e1.period_duration AS current_period_duration,
                                e1.period_price AS current_period_price,
                                e1.period_putmoney AS current_period_putmoney,
                                e1.period_proportion AS current_period_proportion,
                                e1.period_reward AS current_period_reward,
                                e1.period_total AS current_period_total,
                                e1.status AS current_status,
                                e2.period_emotion AS last_period_emotion,
                                e2.period_average AS last_period_average
                            FROM 
                                hack_emotions e1
                            LEFT JOIN 
                                hack_emotions e2 ON e1.period_id - 1 = e2.period_id AND e2.chain_id=e1.chain_id
                            WHERE 
                                e1.chain_id=%s AND e1.status=1
                            """
            values = (chain_id,)
            await cursorSlave.execute(check_query, values)
            combined_info = await cursorSlave.fetchone()
            logger.debug(f"mysql combined_info: {combined_info}")
            if combined_info and period_id == combined_info['current_period_id']:
                current_period_info = {
                    "id": combined_info['current_period_id'],
                    "total": combined_info['current_period_total'],
                    "price": combined_info['current_period_price'],
                    "putmoney": combined_info['current_period_putmoney'],
                    "proportion": combined_info['current_period_proportion'],
                    "duration": combined_info['current_period_duration'],
                    "reward": int(combined_info['current_period_reward']),
                    "timestamp": combined_info['current_period_end'],
                    "last_emotion": combined_info['last_period_emotion'] or 0,
                    "last_average": combined_info['last_period_average'] or 0,
                    "status": combined_info['current_status'],
                }
                logger.debug(f"mysql current_period_info: {current_period_info}")
                await set_redis_data(True, f"hackathon:period:{chain_id}:current", value=json.dumps(current_period_info), ex=60)
            else:
                web3_obj = Web3(Web3.HTTPProvider(web3_rpc_url))
                # Connecting to the RPC Node
                while not web3_is_connected_with_retry(web3_obj):
                    logger.error(f"Ooops! Failed to eth.is_connected. {web3_rpc_url}")
                    time.sleep(10)
                logger.debug(f"web3_rpc_url: '{web3_rpc_url}' {type(web3_rpc_url)}")
                
                # emotion
                emotion_address = web3_config['emotion']
                if not (len(emotion_address) == 42 and emotion_address[:2] == '0x'): 
                    logger.error(f"Invalid emotion_contract address - {address}")
                    return {"code": 401, "success": False, "msg": "Invalid emotion_contract address"}
                # emotion contract
                emotion_contract_address = Web3.to_checksum_address(emotion_address)
                emotion_contract = web3_obj.eth.contract(address=emotion_contract_address, abi=contract_abi_emotion)
                
                period_id = emotion_contract.functions.Issue().call()
                logger.debug(f"period_id: {period_id}")
                time.sleep(0.5)
                period_total = emotion_contract.functions.IssueAddressNum(period_id).call()
                logger.debug(f"period_total: {period_total}")
                time.sleep(0.5)
                period_info = emotion_contract.functions.IssueInformation(period_id).call()
                logger.debug(f"period_info: {period_info}")
                time.sleep(0.5)
                end_timestamp = period_info[0]
                period_price = period_info[1]
                period_putmoney = period_info[2]
                period_proportion = emotion_contract.functions.userProportion().call()
                logger.debug(f"period_proportion: {period_proportion}")
                time.sleep(0.5)
                period_reward = period_total * period_price * period_proportion / 100 + period_putmoney
                logger.debug(f"period_reward: {period_reward}")
                if period_id>1:
                    last_emotion = emotion_contract.functions.IssueEmotion(period_id-1).call()
                    logger.debug(f"last_emotion: {last_emotion}")
                    time.sleep(0.5)
                    last_average = emotion_contract.functions.IssueReward(period_id-1).call()
                    logger.debug(f"last_average: {last_average}")
                else:
                    last_emotion = 0
                    last_average = 0
                
                check_query = """
                                SELECT 
                                    period_id, 
                                    period_duration 
                                FROM hack_emotions 
                                WHERE 
                                    period_id IN (%s, %s)
                                """
                values = (period_id, period_id - 1)
                await cursorSlave.execute(check_query, values)
                emotion_info_list = await cursorSlave.fetchall()
                logger.debug(f"mysql emotion_info_list: {emotion_info_list}")
                period_duration = 0
                for emotion_info in emotion_info_list:
                    if emotion_info['period_id'] == period_id:
                        period_duration = emotion_info['period_duration']
                
                if period_duration == 0:
                    period_duration = 172800
                
                calc_timestamp=current_timestamp-end_timestamp
                current_period_info = {
                    "id": period_id,
                    "total": period_total,
                    "price": period_price,
                    "putmoney": period_putmoney,
                    "proportion": period_proportion,
                    "duration": period_duration,
                    "reward": int(period_reward),
                    "timestamp": end_timestamp,
                    "last_emotion": last_emotion,
                    "last_average": last_average,
                    "status": 2 if calc_timestamp>0 else 1,
                }
                logger.debug(f"contract current_period_info: {current_period_info}")
                logger.debug(f"current: {dt.fromtimestamp(current_timestamp)} end: {dt.fromtimestamp(end_timestamp)} calc: {calc_timestamp}")
                await set_redis_data(True, f"hackathon:period:{chain_id}:current", value=json.dumps(current_period_info), ex=60)

        if current_period_info is None:
            return {
                "code": 200, 
                "success": True, 
                "msg": "success", 
                "data": current_period_info,
            }
        
        current_period_id = current_period_info['id']
        current_period_status = current_period_info['status']
        logger.debug(f"current_period_id: {current_period_id} current_period_status: {current_period_status}")

        ## Last period info
        emotion_list = await get_redis_data(True, f"hackathon:period:{chain_id}:{current_period_id}:list")
        logger.debug(f"redis emotion_list: {emotion_list}")
        if emotion_list is None:
            # Check if the period_id already exists
            check_query = """
                            SELECT 
                                period_id as id,
                                period_end as timestamp,
                                period_emotion as emotion,
                                period_average as average,
                                period_duration as duration,
                                period_reward as reward,
                                period_total as total,
                                emotion_positive as positive,
                                emotion_neutral as neutral,
                                emotion_negative as negative
                            FROM hack_emotions 
                            WHERE
                                chain_id=%s AND status=2
                            ORDER BY period_id DESC 
                            LIMIT 10
                        """
            values = (chain_id,)
            await cursorSlave.execute(check_query,values)
            emotion_list = await cursorSlave.fetchall()
            logger.debug(f"mysql emotion_list: {emotion_list}")
            await set_redis_data(True, f"hackathon:period:{chain_id}:{current_period_id}:list", value=json.dumps(emotion_list), ex=600)

        max_period_id = 0
        if emotion_list:
            max_period_id = emotion_list[0]['id']
        logger.debug(f"max_period_id: {max_period_id}")
        if max_period_id+1 < current_period_id:
            web3_obj = Web3(Web3.HTTPProvider(web3_rpc_url))
            # Connecting to the RPC Node
            while not web3_is_connected_with_retry(web3_obj):
                logger.error(f"Ooops! Failed to eth.is_connected. {web3_rpc_url}")
                time.sleep(10)
            logger.debug(f"web3_rpc_url: '{web3_rpc_url}' {type(web3_rpc_url)}")
            
            # emotion
            emotion_address = web3_config['emotion']
            if not (len(emotion_address) == 42 and emotion_address[:2] == '0x'): 
                logger.error(f"Invalid emotion_contract address - {address}")
                return {"code": 401, "success": False, "msg": "Invalid emotion_contract address"}
            # emotion contract
            emotion_contract_address = Web3.to_checksum_address(emotion_address)
            emotion_contract = web3_obj.eth.contract(address=emotion_contract_address, abi=contract_abi_emotion)
            
            logger.debug(f"max_period_id: {max_period_id} current_period_id: {current_period_id}")
            loop_delay = 1 if current_period_status==2 else 0
            for period_id in range(max_period_id+1, current_period_id+loop_delay):
                logger.debug(f"period_id: {period_id}")
                if period_id == 0:
                    continue
                period_emotion = emotion_contract.functions.IssueEmotion(period_id).call()
                logger.debug(f"period_emotion: {period_emotion}")
                time.sleep(0.5)
                if period_emotion == 0:
                    continue
                period_average = emotion_contract.functions.IssueReward(period_id).call()
                logger.debug(f"period_average: {period_average}")
                time.sleep(0.5)
                period_total = emotion_contract.functions.IssueAddressNum(period_id).call()
                logger.debug(f"period_total: {period_total}")
                time.sleep(0.5)
                period_info = emotion_contract.functions.IssueInformation(period_id).call()
                logger.debug(f"period_info: {period_info}")
                time.sleep(0.5)
                end_timestamp = period_info[0]
                period_price = period_info[1]
                period_putmoney = period_info[2]
                period_proportion = emotion_contract.functions.userProportion().call()
                logger.debug(f"period_proportion: {period_proportion}")
                time.sleep(0.5)
                period_reward = period_total * period_price * period_proportion / 100 + period_putmoney
                logger.debug(f"period_reward: {period_reward}")
                
                if current_timestamp < end_timestamp:
                    logger.info(f"period_id: {period_id} - Please wait {end_timestamp - current_timestamp} Seconds")
                    continue

                emotion_positive = emotion_contract.functions.getIssueEmotionAddrslength(period_id, 1).call()
                logger.debug(f"emotion_positive: {emotion_positive}")
                time.sleep(0.5)
                emotion_neutral = emotion_contract.functions.getIssueEmotionAddrslength(period_id, 2).call()
                logger.debug(f"emotion_neutral: {emotion_neutral}")
                time.sleep(0.5)
                emotion_negative = emotion_contract.functions.getIssueEmotionAddrslength(period_id, 3).call()
                logger.debug(f"emotion_negative: {emotion_negative}")

                update_query = """
                                UPDATE hack_emotions 
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
                                    chain_id=%s AND period_id=%s"""
                values = (end_timestamp, period_putmoney, period_price, period_emotion, int(period_average), int(period_reward), period_total, emotion_positive, emotion_neutral, emotion_negative, 2, chain_id, period_id)
                # logger.debug(f"update_query: {update_query} values: {values}")
                await cursor.execute(update_query, values)
                await cursor.connection.commit()
                logger.debug(f"update hack_emotions - status=2")

            # Check if the period_id already exists
            check_query = """
                            SELECT 
                                period_id as id,
                                period_end as timestamp,
                                period_emotion as emotion,
                                period_average as average,
                                period_duration as duration,
                                period_reward as reward,
                                period_total as total,
                                emotion_positive as positive,
                                emotion_neutral as neutral,
                                emotion_negative as negative 
                            FROM hack_emotions 
                            WHERE 
                                chain_id=%s AND status=2
                            ORDER BY period_id DESC 
                            LIMIT 10
                        """
            values = (chain_id,)
            await cursorSlave.execute(check_query, values)
            emotion_list = await cursorSlave.fetchall()
            logger.debug(f"mysql emotion_list: {emotion_list}")
            await set_redis_data(True, f"hackathon:period:{chain_id}:{current_period_id}:list", value=json.dumps(emotion_list), ex=600)
        
        user_emotion_list = await get_redis_data(False, f"hackathon:period:{chain_id}:{current_period_id}:{address}:list")
        logger.debug(f"redis user_emotion_list: {user_emotion_list}")
        if user_emotion_list is None:
            check_query = """
                            SELECT 
                                period_id as id,
                                MAX(period_emotion) as emotion 
                            FROM hack_emotion_onchain 
                            WHERE 
                                address = %s AND status = 1 
                            GROUP BY period_id 
                            ORDER BY id DESC 
                            LIMIT 11
                            """
            values = (address,)
            # print(f"check_query: {check_query}, values: {values}")
            await cursor.execute(check_query, values)
            user_emotion_list = await cursor.fetchall()
            logger.debug(f"mysql user_emotion_list: {user_emotion_list}")
            await set_redis_data(False, f"hackathon:period:{chain_id}:{current_period_id}:{address}:list", value=json.dumps(user_emotion_list), ex=600)

        for emotion in emotion_list:
            emotion_id = emotion['id']
            emotion['user_emotion']=0
            for user_emotion in user_emotion_list:
                if emotion_id == user_emotion['id']:
                    emotion['user_emotion'] = user_emotion['emotion']
        
        return {
            "code": 200, 
            "success": True, 
            "msg": "success", 
            "data": emotion_list,
        }
    except Exception as e:
        logger.error(f"/api/emotion/history - {address} except ERROR: {str(e)}")
        return {"code": 500, "success": False, "msg": "Server error"}

