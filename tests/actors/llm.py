import os
import asyncio
import logging
import argparse
from mop.core import EventDrivingActor
from mop.utils import ExceptionFormatter

async def main(actor: EventDrivingActor):
    logging.info("starting actor")
    async for x in actor(repeat=True):
        print(x)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler()
        ]
    )
    for handler in logging.getLogger().handlers:
        handler.setFormatter(ExceptionFormatter("%(levelname)s: %(message)s"))
    agp  = argparse.ArgumentParser()
    agp.add_argument('--redis_host',     required=False, type=str)
    agp.add_argument('--redis_password', required=False, type=str)
    args = agp.parse_args()

    actor = EventDrivingActor(
        
        redis_host=os.environ.get('redis_host', args.redis_host),
        redis_client=os.environ.get('redis_client'),
        redis_password=os.environ.get('redis_password', args.redis_password),
        redis_channel_requests=os.environ.get('redis_channel_requests'),
        redis_channel_replies=os.environ.get('redis_channel_replies'),
        function="list",
        args={}
    )

    asyncio.run(main(actor))