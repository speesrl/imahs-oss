import os
import uuid
import asyncio
import logging
import argparse
import ollama
from mop.core import EventDrivingActor
from mop.clients import LibreTranslate, ping
from mop.utils import ExceptionFormatter
from mop.benchmarks import profileit

uid = os.environ.get("SUPERVISOR_PROCESS_NUM")

async def main(args):

    libretranslate_actor = EventDrivingActor(
        
        redis_host=os.environ.get('redis_host', args.redis_host),
        redis_client=os.environ.get('redis_client'),
        redis_password=os.environ.get('redis_password', args.redis_password),
        redis_channel_requests=f"{os.environ.get('redis_channel_requests')}:mt:{uid}",
        redis_channel_replies=f"{os.environ.get('redis_channel_replies')}:mt:{uid}",
        function="run",
        args={'text': 'ciao come stai?', 'src': 'it', 'tgt': 'en'}
    )
    libretranslate_client = LibreTranslate(
        url=os.environ.get('libretranslate_host')
    )
    ollama_actor = EventDrivingActor(
        redis_host=os.environ.get('redis_host', args.redis_host),
        redis_client=os.environ.get('redis_client'),
        redis_password=os.environ.get('redis_password', args.redis_password),
        redis_channel_requests=f"{os.environ.get('redis_channel_requests')}:llm:{uid}",
        redis_channel_replies=f"{os.environ.get('redis_channel_replies')}:llm:{uid}",
        function="list",
        args={}
    )
    ollama_client = ollama.Client(
        host=os.environ.get('ollama_host')
    )
    await asyncio.gather(
        profileit('libretranslate', uid, 100, libretranslate_actor, lambda: libretranslate_client(text='ciao come stai?', src='it', tgt='en')),
        profileit('ollama', 100, uid, ollama_actor, ollama_client.list)
    )

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
    asyncio.run(main(args))