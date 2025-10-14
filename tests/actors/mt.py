import os
import uuid
import asyncio
import logging
import argparse
import time
import json
from mop.clients import LibreTranslate
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
        redis_channel_requests=f"{os.environ.get('redis_channel_requests')}:mt:{uid}",
        redis_channel_replies=f"{os.environ.get('redis_channel_replies')}:{uid}",
        function="run",
        args={'text': 'ciao come stai?', 'src': 'it', 'tgt': 'en'}
    )

    client = LibreTranslate(
        url=os.environ.get('libretranslate_host')
    )

    asyncio.run(profileit('libretranslate', 100, actor, lambda: client(text='ciao come stai?', src='it', tgt='en')))