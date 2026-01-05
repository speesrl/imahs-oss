# Model Orchestration Protocol

an Event-Driven Reactive Architecture (EDA) with an Actor/Reactor Model for Scalable Context Exchange in Large Model Applications.

## Installation
```sh
pip install https://github.com/speesrl/imahs-oss
```

## Usage
`MOP` works by providing the user with a way of creating asynchronous reactors (data producing logic units) in separate processes, and actors which can induce a reaction by communicating their requests over a redis channel.

### Reactor Example:
```py
import ollama # pip install ollama==0.5.3
from mop.core import EventDrivenReactor

class Ollama(EventDrivenReactor, ollama.Client):
    def __init__(self, *, redis_host, redis_client, redis_password, redis_channel_requests: str, sleep: float = 0.1, host : str = 'http://localhost:11434', **kwargs):
        EventDrivenReactor.__init__(
            self,
            redis_host=redis_host, 
            redis_client=redis_client, 
            redis_password=redis_password, 
            redis_channel_requests=redis_channel_requests, 
            sleep=sleep
        )
        ollama.Client.__init__(self, host=host, **kwargs)

async def main(args):
    lm = Ollama(
        redis_host=args.redis_host,
        redis_client=args.redis_client,
        redis_password=args.redis_password,
        redis_channel_requests=f"{args.redis_channel_requests}:llm",
        host=args.ollama_host
    )
    await asyncio.gather(
        lm.event_driven_loop()
    )

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.StreamHandler()
        ]
    )
    agp  = argparse.ArgumentParser()
    agp.add_argument('--redis_host',     required=False, type=str)
    agp.add_argument('--redis_password', required=False, type=str)
    agp.add_argument('--redis_client', required=False, type=str)
    agp.add_argument('--redis_channel_requests', required=False, type=str)
    agp.add_argument('--ollama_host', required=False, type=str)
    args = agp.parse_args()
    asyncio.run(main(args))
```

### Actor Example:
```py
import os
import uuid
import asyncio
import logging
import argparse
from mop.core import EventDrivingActor


async def main(args):
    uid = uuid.uuid4().hex
    ollama_actor = EventDrivingActor(
        redis_host=args.redis_host,
        redis_client=args.redis_client,
        redis_password=args.redis_password,
        redis_channel_requests=f"{args.redis_channel_requests}:llm:{uid}",
        redis_channel_replies=f"{args.redis_channel_replies}:llm:{uid}",
        function="list",
        args={}
    )
    async for x in ollama_actor(repeat=repeat, timeout=timeout):
        await asyncio.sleep(actor.sleep/10)
        yield x

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.StreamHandler()
        ]
    )
    agp  = argparse.ArgumentParser()
    agp.add_argument('--redis_host',     required=False, type=str)
    agp.add_argument('--redis_password', required=False, type=str)
    agp.add_argument('--redis_client', required=False, type=str)
    agp.add_argument('--redis_channel_requests', required=False, type=str)
    agp.add_argument('--redis_channel_replies', required=False, type=str)
    args = agp.parse_args()
    asyncio.run(main(args))
```

## Usefulness 
In many types of applications; concurrency, elasticity, and fault isolation are needed to sustain heterogeneous, long-lived interactions with distributed dynamic tool servers. These constraints become critical in event-loop applications such as graphical or distributed clients, where scalability and non-blocking communication are essential.

## Notices
See the [NOTICE](NOTICE) file for attribution, funding, and third-party notices.
