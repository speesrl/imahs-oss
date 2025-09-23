import asyncio
import argparse
from imahs.lib.core2 import EventDrivingActor

async def main(actor):
    async for x in actor():
        print(x)

if __name__ == "__main__":
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