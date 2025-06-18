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

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field

from utils.cache import get_redis_data, set_redis_data, del_redis_data, increment_redis_data
from utils.database import get_db, get_db_slave
from utils.security import get_current_address
from utils.log import log as logger
from config import set_envsion, get_envsion, APP_CONFIG, AI_AGENT_PROMPT, AI_CONFIG

router = APIRouter()


## ai

# --------------------------------------------------------------------------------------------------
def contains_letter(text):
    pattern = re.compile(r'[a-zA-Z]')
    return bool(pattern.search(text))

def update_conversation_history(conversation_history, role, message):
    if len(conversation_history) == 0 and role=="user":
        logger.warning("The first input cannot be user, skip")
        return
    if not message.strip():
        logger.warning("Input is empty, skip")
        return
    if len(message) > 2000:
        logger.warning("Input too long, truncated")
        message = message[:2000]
    if conversation_history[-1]['role'] in ["200","400","405"]:
        logger.warning("Session ended, skipped")
        return
    if conversation_history[-1]['role'] == role:
        logger.warning("Input exists, delete and re-enter")
        conversation_history.pop()
    conversation_history.append({"role": role, "content": message})

def contains_keywords_regex(text, keywords):
    include_pattern = re.compile(r'(' + '|'.join(re.escape(keyword) for keyword in keywords) + r')', re.IGNORECASE)
    
    if include_pattern.search(text):
        return True
    return False

def contains_keywords_regex_two(text, keywords, exclude_keywords):
    include_pattern = re.compile(r'(' + '|'.join(re.escape(keyword) for keyword in keywords) + r')', re.IGNORECASE)
    exclude_pattern = re.compile(r'(' + '|'.join(re.escape(keyword) for keyword in exclude_keywords) + r')', re.IGNORECASE)
    
    if include_pattern.search(text):
        if not exclude_pattern.search(text):
            return True
    return False

def extract_keywords(text, keywords):
    pattern = re.compile(r'(' + '|'.join(re.escape(keyword) for keyword in keywords) + r')', re.IGNORECASE)
    matches = pattern.findall(text)
    logger.debug(f"matches: {matches}")
    return matches

def aichat_response_sync(address, conversation_history):
    """AI Chat"""
    today = time.strftime("%Y-%m-%d", time.localtime())
    logger.debug(f"today: {today}")
    status=0
    emotion_keyword=''
    include_keywords = ["analysis:", "conjectures:", "emotions*", "career*", "relationships*", "life*"]
    keywords = ["positive", "neutral", "negative"]
    exclude_keywords = ["question:"]
    for CONFIG in AI_CONFIG:
        try:
            logger.debug(f"CONFIG: {CONFIG}")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {CONFIG['api_key']}",
            }
            data = {
                "model": CONFIG['model'],
                "messages": conversation_history,
                "stream": True,
            }

            response = requests.post(CONFIG['url'], headers=headers, json=data, stream=True, timeout=10)
            if response.status_code != 200:
                continue
            
            ai_response = ""
            for line in response.iter_lines():
                if not line:
                    continue
                
                buffer = line.decode('utf-8')
                if buffer.startswith("data: "):
                    buffer = buffer[6:]
                if buffer.startswith("\n"):
                    buffer = buffer[1:]
                
                try:
                    json_obj = json.loads(buffer)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {buffer}")
                    continue

                if ('DONE' in json_obj) or ('choices' in json_obj and json_obj['choices'][0]['finish_reason'] == 'stop'): # AI streaming output ends
                    logger.info(f"ai_response: {ai_response}")
                    update_conversation_history(conversation_history, "assistant", ai_response)
                    conversation_history.pop(0)

                    # Emotion Recognition: check emotion key / conversation_history>6
                    if contains_keywords_regex(ai_response.lower(), include_keywords) or len(conversation_history) > 6:
                        status=200
                        emotion_list = extract_keywords(ai_response.lower(), keywords)
                        if len(emotion_list)>0:
                            emotion_keyword = emotion_list[0]
                            logger.info(f"Find emotion keywords in response: {emotion_keyword}")
                            update_conversation_history(conversation_history, "200", emotion_keyword)
                        if len(conversation_history) > 12: # If more than 12 times, the system will automatically roll back.
                            status=405
                            update_conversation_history(conversation_history, "405", "No chat times")
                            asyncio.run(set_redis_data(False, f"hackathon:aichat:{address}:{today}:check", value=405, ex=86400))
                    elif 'training failed' in ai_response.lower() or 'test failed' in ai_response.lower():
                        conversation_history.pop()

                        status=400
                        update_conversation_history(conversation_history, "400", 'Training failed')
                        asyncio.run(set_redis_data(False, f"hackathon:aichat:{address}:{today}:check", value=400, ex=86400))

                    asyncio.run(set_redis_data(False, f"hackathon:aichat:{address}:pending", value=json.dumps(conversation_history), ex=1800))
                    break
                elif 'choices' in json_obj and json_obj['choices'][0]['delta'].get('content', '') != '': # AI streaming output
                    response_chunk = json_obj['choices'][0]['delta'].get('content', '')
                    ai_response += response_chunk
                    
                    status = 206
                    # yield response_chunk
                    response_chunk = response_chunk.replace('\n', '<br/>')
                    yield '{"code": 206, "msg": "'+response_chunk+'"}'
            else:
                continue
            break
        except requests.exceptions.HTTPError as http_err:
            status=500
            logger.error(f"HTTP error occurred: {http_err}")
            if response.status_code == 401:
                continue
            else:
                raise
        except Exception as e:
            status=500
            logger.error(f"Exception Error: {e}")
            continue
    
    logger.debug(f"status: {status}")
    if status == 500:
        yield '{"code": 500, "success": false, "msg": "Network error"}'
    elif status == 400:
        yield '{"code": 400, "success": false, "msg": "Training failed"}'
    elif status == 200 and emotion_keyword:
        asyncio.run(set_redis_data(False, f"hackathon:aichat:{address}:{today}:check", value=emotion_keyword, ex=86400))
        yield '{"code": 200, "success": true, "msg": "'+emotion_keyword+'"}'


class AIChatRequest(BaseModel):
    message: str
    mark: bool | None = False
@router.post("/chat")
async def ai_chat(post_request: AIChatRequest, address: Dict = Depends(get_current_address), cursorSlave=Depends(get_db_slave)):
    """AI Agent Conversation"""
    logger.info(f"POST /api/ai/chat - {address}")
    if cursorSlave is None:
        logger.error(f"/api/ai/chat - {address} cursorSlave: None")
        return {"code": 500, "success": False, "msg": "cursor error"}

    try:
        mark = post_request.mark
        message = post_request.message
        logger.info(f"Received message: {message}")

        today = time.strftime("%Y-%m-%d", time.localtime())
        logger.debug(f"today: {today}")
        aichat_check = await get_redis_data(False, f"hackathon:aichat:{address}:{today}:check")
        logger.debug(f"redis aichat_check: {aichat_check}")
        if not aichat_check:
            check_query = """
                    SELECT 
                        detail 
                    FROM gaea_emotion_training 
                    WHERE 
                        address = %s and date = %s
                    ORDER BY id DESC limit 1
                    """
            values = (address,today)
            await cursorSlave.execute(check_query, values)
            checkin_info = await cursorSlave.fetchone()
            logger.debug(f"mysql checkin_info: {checkin_info}")
            if checkin_info:
                aichat_check=checkin_info['detail']
            else:
                aichat_check=''
            await set_redis_data(False, f"hackathon:aichat:{address}:{today}:check", value=aichat_check, ex=86400)
        aichat_check_str = str(aichat_check)
        if len(aichat_check_str) > 0:
            if aichat_check_str == '400':
                return {"code": 400, "success": False, "msg": "Training failed"}
            elif aichat_check_str == '405':
                return {"code": 405, "success": False, "msg": "No chat times"}
            else:
                if len(aichat_check_str.split('_')) == 1:
                    emotional = aichat_check_str
                else:
                    keywords = ["none", "positive", "neutral", "negative"]
                    emotional_id = int(aichat_check_str.split('_')[0])
                    logger.debug(f"emotional_id: {emotional_id}")
                    emotional = keywords[emotional_id]
                if emotional != 'none':
                    return {"code": 200, "success": True, "msg": emotional}

        conversation_history = []
        if mark: # Clean up records
            await set_redis_data(False, f"hackathon:aichat:{address}:pending", value=json.dumps(conversation_history), ex=1800)
        else:
            # Chat history cache
            conversation_list = await get_redis_data(False, f"hackathon:aichat:{address}:pending")
            if conversation_list:
                last_conversation_one = ''
                for conversation_one in conversation_list:
                    if conversation_one != last_conversation_one:
                        conversation_history.append(conversation_one)
                    last_conversation_one = conversation_one
                if len(conversation_list) >= 1:
                    update_conversation_history(conversation_history, "user", message)
                    await set_redis_data(False, f"hackathon:aichat:{address}:pending", value=json.dumps(conversation_history), ex=1800)
        logger.debug(f"conversation_history: {conversation_history}")
        if len(conversation_history) >= 6 and conversation_history[-1]['role'] == "200":
            aichat_check = conversation_history[-1]['content']
            await set_redis_data(False, f"hackathon:aichat:{address}:{today}:check", value=aichat_check, ex=86400)
            return {"code": 200, "success": True, "msg": aichat_check}
        if len(conversation_history) > 12:
            update_conversation_history(conversation_history, "405", "No chat times")
            await set_redis_data(False, f"hackathon:aichat:{address}:{today}:check", value=405, ex=86400)
            return {"code": 405, "success": False, "msg": "No chat times"}
        
        username = address[:4] + '...' + address[-4:]
        user_gaeaagent_prompt = AI_AGENT_PROMPT
        conversation_history.insert(0, {"role": "system", "content": user_gaeaagent_prompt.replace('XXX',username).replace('YYMMDD',today)})

        return StreamingResponse(aichat_response_sync(address, conversation_history), media_type="text/plain")
    except Exception as e:
        logger.error(f"/api/ai/chat except ERROR: {str(e)}")
        return {"code": 500, "success": False, "msg": "Server error"}

@router.get("/chat-history")
async def ai_chat_history(address: Dict = Depends(get_current_address), cursor=Depends(get_db)):
    """AI Agent Conversation Recording"""
    logger.info(f"POST /api/ai/chat-history - {address}")
    if cursor is None:
        logger.error(f"/api/ai/chat-history - {address} cursor: None")
        return {"code": 500, "success": False, "msg": "cursor error"}

    try:
        today = time.strftime("%Y-%m-%d", time.localtime())
        logger.debug(f"today: {today}")

        conversation_history = []
        conversation_list = await get_redis_data(False, f"hackathon:aichat:{address}:pending")
        if conversation_list:
            last_conversation_one = ''
            for conversation_one in conversation_list:
                if conversation_one != last_conversation_one:
                    conversation_one.update({"content": conversation_one['content'].replace('\n', '<br/>')})
                    conversation_history.append(conversation_one)
                last_conversation_one = conversation_one
            if len(conversation_history) > 12:
                update_conversation_history(conversation_history, "405", "No chat times")
                await set_redis_data(False, f"hackathon:aichat:{address}:{today}:check", value=405, ex=86400)
        logger.debug(f"conversation_history: {conversation_history}")
        return {
            "code": 200, 
            "success": True, 
            "msg": "success", 
            "data": conversation_history,
        }
    except Exception as e:
        logger.error(f"/api/ai/chat-history except ERROR: {str(e)}")
        return {"code": 500, "success": False, "msg": "Server error"}

# --------------------------------------------------------------------------------------------------

@router.get("/list")
async def ai_list(address: Dict = Depends(get_current_address), cursorSlave=Depends(get_db_slave)):
    """7 days of deep training data"""
    logger.info(f"POST /api/ai/list - {address}")
    if cursorSlave is None:
        logger.error(f"/api/ai/list - {address} cursorSlave: None")
        return {"code": 500, "success": False, "msg": "cursor error"}

    try:
        today = time.strftime("%Y-%m-%d", time.localtime())
        logger.debug(f"today: {today}")
        seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=4)
        logger.debug(f"seven_days_ago: {seven_days_ago}")
        seven_days_ago_timestamp = int(seven_days_ago.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        logger.debug(f"seven_days_ago_timestamp: ({type(seven_days_ago_timestamp).__name__}){seven_days_ago_timestamp}")

        # AI Training
        aitrain_complete=0
        aitrain_detail=''
        aitrain_info=await get_redis_data(False, f"hackathon:aitrain:{address}:{today}:detail")
        logger.debug(f"redis aitrain_info: {aitrain_info}")
        if not aitrain_info:
            check_query = "SELECT detail,status FROM gaea_emotion_training WHERE address = %s and status = 1 and date = %s limit 1"
            values = (address, today)
            # print(f"check_query: {check_query}, values: {values}")
            await cursorSlave.execute(check_query, values)
            aitrain_info = await cursorSlave.fetchone()
            logger.debug(f"mysql aitrain_info: {aitrain_info}")
            if aitrain_info:
                await set_redis_data(False, f"hackathon:aitrain:{address}:{today}:detail", value=json.dumps(aitrain_info), ex=86400)
        if aitrain_info:
            aitrain_complete=aitrain_info['status']
            aitrain_detail=aitrain_info['detail']


        ## Get the most recent 6 deep training data
        checkin_list = await get_redis_data(False, f"hackathon:deeptrain:{address}:{today}:list")
        logger.debug(f"redis checkin_list: {checkin_list}")
        if not checkin_list:
            check_query = """
                    WITH ranked_data AS (
                        SELECT date,detail,status,ROW_NUMBER() OVER (PARTITION BY date ORDER BY status ASC) as rn
                        FROM gaea_emotion_training 
                        WHERE address = %s AND status = 2 AND created_time > FROM_UNIXTIME(%s) 
                    )
                    SELECT date, detail, status
                    FROM ranked_data
                    WHERE rn = 1
                    ORDER BY date DESC LIMIT 6
                    """
            values = (address,seven_days_ago_timestamp)
            await cursorSlave.execute(check_query, values)
            checkin_list = await cursorSlave.fetchall()
            logger.debug(f"mysql checkin_list: {checkin_list}")
            await set_redis_data(False, f"hackathon:deeptrain:{address}:{today}:list", value=json.dumps(checkin_list), ex=60)
        # Continuous sign-in reward
        continuous = 0  # Consecutive sign-ins
        completed_today = 0  # Completed today's mark
        completed_detail = ''  # AI Emotions Today
        seven_data = []
        for checkin_one in checkin_list:
            logger.debug(f"checkin_one: {checkin_one}")
            checkin_one_date = checkin_one['date'][:10]
            logger.debug(f"checkin_one_date: {checkin_one_date}")
            if checkin_one_date == today:
                completed_today = checkin_one['status'] if ('status' in checkin_one and int(checkin_one['status'])>0) else 1
                completed_detail = checkin_one['detail']
            else:
                continuous += 1
                day = (datetime.datetime.now() + datetime.timedelta(days=-continuous)).strftime("%Y-%m-%d")
                if checkin_one_date != day:
                    continuous -= 1
                    break
            seven_data.append({"date":checkin_one_date,"detail":checkin_one['detail'],"status":checkin_one['status']})
        logger.debug(f"continuous: {continuous} completed_today: {completed_today}")
        if completed_today: continuous += 1
        if continuous == 8:  continuous = 7
        logger.debug(f"continuous: {continuous}")

        seven_data.sort(key=lambda x: x['date'])
        for one_data in seven_data:
            one_date = one_data['date'][:10]
            if len(one_date.split('-'))==3:
                one_data['date'] = one_date.split('-')[2] + '/' + one_date.split('-')[1] + '/' + one_date.split('-')[0]
            else:
                one_data['date'] = one_date

        return {
            "code": 200,
            "success": True,
            "msg": "Success",
            "data": {
                "today": aitrain_detail if aitrain_complete else '',
                "cycle": seven_data,
            }
        }
    except Exception as e:
        logger.error(f"/api/ai/list - {address} except ERROR: {str(e)}")
        return {"code": 500, "success": False, "msg": "Server error"}


class CheckInRequest(BaseModel):
    detail: str = Field(..., description="Emotion Details")
@router.post("/complete")  # {detail}
async def ai_complete(post_request: CheckInRequest, address: Dict = Depends(get_current_address), cursor=Depends(get_db)):
    """AI training"""
    logger.info(f"POST /api/ai/complete - {address}")
    if cursor is None:
        logger.error(f"/api/ai/complete - {address} cursor: None")
        return {"code": 500, "success": False, "msg": "cursor error"}

    try:
        today = time.strftime("%Y-%m-%d", time.localtime())
        logger.debug(f"today: {today}")

        # AI Training
        aitrain_complete=0
        aitrain_info=await get_redis_data(False, f"hackathon:aitrain:{address}:{today}:detail")
        logger.debug(f"redis aitrain_info: {aitrain_info}")
        if not aitrain_info:
            check_query = "SELECT detail,status FROM gaea_emotion_training WHERE address = %s and status = 1 and date = %s limit 1"
            values = (address, today)
            # print(f"check_query: {check_query}, values: {values}")
            await cursor.execute(check_query, values)
            aitrain_info = await cursor.fetchone()
            logger.debug(f"mysql aitrain_info: {aitrain_info}")
            if aitrain_info:
                await set_redis_data(False, f"hackathon:aitrain:{address}:{today}:detail", value=json.dumps(aitrain_info), ex=86400)
        if aitrain_info:
            aitrain_complete=aitrain_info['status']

        if aitrain_complete > 0:
            await increment_redis_data(False, f"hackathon:aitrain:{address}:{today}:detail", value_key="status", ex=86400)
            logger.error(f"STATUS: 400 ERROR: Training already completed - {address}")
            return {"code": 400, "success": False, "msg": f"Training already completed"}

        ## Block multiple user requests 60
        redis_pending_complete = await get_redis_data(False, f"hackathon:aitrain:{address}:{today}:pending")
        if redis_pending_complete:
            return {"code": 400, "success": False, "msg": "Please wait for the last completion"}
        await set_redis_data(False, f"hackathon:aitrain:{address}:{today}:pending", value=1, ex=60)

        if aitrain_complete: 
            logger.error(f"STATUS: 400 ERROR: Training already completed - {address}")
            return {"code": 400, "success": False, "msg": f"Training already completed"}
        else:
            # Check if record exists
            check_query = "SELECT * from gaea_emotion_training WHERE address = %s and status = 1 and date = %s"
            values = (address, today)
            logger.debug(f"check_query: {check_query} values: {values}")
            await cursor.execute(check_query, values)
            exist_train_check = await cursor.fetchone()
            logger.debug(f"mysql exist_train_check: {exist_train_check}")
            if exist_train_check:
                await del_redis_data(False, f"hackathon:aitrain:{address}:{today}:detail")
                logger.error(f"STATUS: 400 ERROR: Training already completed - {address}")
                return {"code": 400, "success": False, "msg": f"Training already completed"}

            # Start emotion training
            insert_query = """
                            INSERT INTO gaea_emotion_training (address, detail, status, date) 
                            SELECT %s, %s, %s, %s
                            WHERE NOT EXISTS (SELECT id FROM gaea_emotion_training WHERE address = %s and status = 1 and date = %s)
                            """
            values = (address, post_request.detail, 1, today, address, today)
            await cursor.execute(insert_query, values)
            await cursor.connection.commit()

            # Delete cache
            await del_redis_data(False, f"hackathon:deeptrain:{address}:{today}:list")
            await del_redis_data(False, f"hackathon:trainall:{address}:count")
            await del_redis_data(False, f"hackathon:trainall:{address}:1:10:list")
            await del_redis_data(False, f"hackathon:aitrain:{address}:{today}:detail")

            return {
                "code": 200,
                "success": True,
                "msg": "Success",
                "data": {
                    "detail": post_request.detail
                }
            }
    except Exception as e:
        logger.error(f"/api/ai/complete - {address} except ERROR: {str(e)}")
        return {"code": 500, "success": False, "msg": "Server error"}


@router.get("/history")  # ?page=0&limit=10
async def ai_history(page: int | None = 1, limit: int | None = 10, address: Dict = Depends(get_current_address), cursorSlave=Depends(get_db_slave)):
    """Training history data"""
    logger.info(f"GET /api/ai/history - {address}")
    if cursorSlave is None:
        logger.error(f"/api/ai/history - {address} cursorSlave: None")
        return {"code": 500, "success": False, "msg": "cursor error"}

    try:
        history_count = await get_redis_data(False, f"hackathon:trainall:{address}:count")
        logger.debug(f"redis history_count: {history_count}")
        if history_count is None:
            check_query = "SELECT count(*) as len FROM gaea_emotion_training WHERE address = %s"
            values = (address)
            await cursorSlave.execute(check_query, values)
            all_info = await cursorSlave.fetchone()
            logger.debug(f"mysql all_info: {all_info}")
            if all_info is None:
                history_count = 0
            else:
                history_count = all_info['len']
            await set_redis_data(False, f"hackathon:trainall:{address}:count", value=history_count, ex=600)

        if history_count == 0:
            return {
                "code": 200,
                "success": True,
                "msg": "Success",
                "data": [],
                "total": 0,
            }

        if page == 0: page = 1
        history_list = await get_redis_data(False, f"hackathon:trainall:{address}:{page}:{limit}:list")
        logger.debug(f"redis history_list: {history_list}")
        if history_list is None:
            check_query = "SELECT date,detail,status FROM gaea_emotion_training WHERE address = %s order by id DESC limit %s, %s "
            values = (address, limit * (page - 1), limit)
            await cursorSlave.execute(check_query, values)
            history_list = await cursorSlave.fetchall()
            logger.debug(f"mysql history_list: {history_list}")
            await set_redis_data(False, f"hackathon:trainall:{address}:{page}:{limit}:list", value=json.dumps(history_list), ex=600)

        history_data = []
        for history_one in history_list:
            if contains_letter(history_one['detail']):
                continue
            one_date = history_one['date'][:10]
            if len(one_date.split('-'))==3:
                new_one_date = one_date.split('-')[2] + '/' + one_date.split('-')[1] + '/' + one_date.split('-')[0]
            else:
                new_one_date = one_date
            history_data.append({"date":new_one_date,"detail":history_one['detail'],"status":history_one['status']})
        logger.debug(f"history_data: {history_data}")

        return {
            "code": 200,
            "success": True,
            "msg": "Success",
            "data": history_data if history_data else [],
            "total": history_count if history_count else 0,
        }
    except Exception as e:
        logger.error(f"/api/ai/history - {address} except ERROR: {str(e)}")
        return {"code": 500, "success": False, "msg": "Server error"}

# --------------------------------------------------------------------------------------------------

