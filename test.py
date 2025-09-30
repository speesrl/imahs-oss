import asyncio
import logging
import argparse
from imahs.lib.core2 import EventDrivingActor
from imahs.lib.utils import ExceptionFormatter

async def main(actor):
    async for x in actor():
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
    agp.add_argument('--redis_host',     required=True, type=str)
    agp.add_argument('--redis_password', required=True, type=str)
    args = agp.parse_args()

    actor = EventDrivingActor(
        redis_host=args.redis_host,
        redis_client="imahs",
        redis_password=args.redis_password,
        redis_target_channel="imahs:oss",
        redis_replyto_channel="imahs:actor",
        function="list",
        args={}
    )

    asyncio.run(main(actor))