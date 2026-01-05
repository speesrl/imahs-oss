import os 
import time 
import json
import logging 
import asyncio
from mop.core import EventDrivingActor, Serializer
from pyprofyler import PyProfyler


@PyProfyler
async def func_test(repeat, timeout, sleep_for, func, *args, **kwargs):
    r = func(*args, **kwargs)
    while True:
        await asyncio.sleep(sleep_for)
        yield r
        if repeat:
            if not any(isinstance(repeat, cls) for cls in [bool, int]):
                continue
            r = func(*args, **kwargs)
            if isinstance(repeat, int):
                repeat -= 1
                t = time.time()
        elif timeout:
            if time.time()-t > timeout:
                break 
    yield r

@PyProfyler
async def actor_test(repeat, timeout, actor: EventDrivingActor):
    async for x in actor(repeat=repeat, timeout=timeout):
        await asyncio.sleep(actor.sleep/10)
        yield x

async def profileit(name, uid, repeat, actor: EventDrivingActor, func, *args, **kwargs):
    serializer = Serializer()
    actor_yields = []
    async for v in actor_test(repeat=repeat, timeout=10, actor=actor):
        await asyncio.sleep(actor.sleep/10)
        actor_yields+=[v]
    func_yields = []
    async for v in func_test(repeat=repeat, timeout=10, sleep_for=actor.sleep, func=func, *args, **kwargs):
        await asyncio.sleep(actor.sleep/10)
        func_yields+=[serializer(v)]
    result = dict()
    result['actor'] = json.loads(str(actor_test))
    result['actor']['yields'] = actor_yields
    result['client'] = json.loads(str(func_test))
    result['client']['yields'] = func_yields
    result['repeated'] = repeat
    result['func'] = actor.function
    result['uid'] = uid
    logging.info(result)
    with open(f'./files/{name}_test_{os.environ.get("SUPERVISOR_PROCESS_NUM")}.json', 'w') as f:
        json.dump(result, f, indent=4)
    while True:
        await asyncio.sleep(1)
    
