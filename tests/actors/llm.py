import os
import uuid
import asyncio
import logging
import argparse
import ollama
import time
import json
from mop.core import EventDrivingActor
from mop.utils import ExceptionFormatter
from mop.benchmarks import profileit

uid = uuid.uuid4().hex 


    
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.StreamHandler()
        ]
    )
    for handler in logging.getLogger().handlers:
        handler.setFormatter(ExceptionFormatter("%(message)s"))
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

    asyncio.run(profileit('ollama', 100, actor, client.list))