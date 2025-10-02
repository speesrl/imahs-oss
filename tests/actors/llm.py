import os
import uuid
import asyncio
import logging
import argparse
import ollama
import time
from mop.core import EventDrivingActor
from mop.utils import ExceptionFormatter
from pyprofyler import PyProfyler

uid = uuid.uuid4().hex 

@PyProfyler
async def ollama_test(client: ollama.Client, repeat, timeout):
    r = client.list()
    while True:
        await asyncio.sleep(.1)
        yield r
        if repeat:
            if not any(isinstance(repeat, cls) for cls in [bool, int]):
                continue
            r = client.list()
            if isinstance(repeat, int):
                repeat -= 1
                t = time.time()
        elif timeout:
            if time.time()-t > timeout:
                break 
    yield r

@PyProfyler
async def actor_test(actor: EventDrivingActor):
    async for x in actor(repeat=10, timeout=1):
        await asyncio.sleep(0.00000000001)
        yield x

async def main(actor: EventDrivingActor, client: ollama.Client):
    async for v in actor_test(actor):
        await asyncio.sleep(0.00000000001)
        logging.info(v)
    logging.info(str(actor_test))
    async for v in ollama_test(client, repeat=10, timeout=1):
        await asyncio.sleep(0.00000000001)
        logging.info(v)
    logging.info(str(ollama_test))
    while True:
        await asyncio.sleep(1)
    
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.StreamHandler()
        ]
    )
    for handler in logging.getLogger().handlers:
        handler.setFormatter(ExceptionFormatter("%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"))
    agp  = argparse.ArgumentParser()
    agp.add_argument('--redis_host',     required=False, type=str)
    agp.add_argument('--redis_password', required=False, type=str)
    args = agp.parse_args()

    actor = EventDrivingActor(
        
        redis_host=os.environ.get('redis_host', args.redis_host),
        redis_client=os.environ.get('redis_client'),
        redis_password=os.environ.get('redis_password', args.redis_password),
        redis_channel_requests=f"{os.environ.get('redis_channel_requests')}:{uid}",
        redis_channel_replies=f"mop:replies:{uid}",
        function="list",
        args={}
    )

    client = ollama.Client(
        host=os.environ.get('ollama_host')
    )

    asyncio.run(main(actor, client))