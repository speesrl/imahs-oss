"""

"""

import uuid
import json
import ollama
import logging
import asyncio
import inspect
import datetime
import functools
import time
import mop.clients

class EventDrivingActor:
    def __init__(self, *, redis_host, redis_client, redis_password, redis_channel_requests, redis_channel_replies, function, args, sleep=.1):
        self.redis_channel_replies = redis_channel_replies
        self.function = function
        self.euuid = uuid.uuid4().hex
        self.sleep = max(sleep, .1)
        self.redis = mop.clients.Redis(
                host=redis_host, 
                client_name=redis_client,
                password=redis_password
        )
        self.args = args
        self.redis_channel_requests = redis_channel_requests
        
    async def __call__(self, repeat=False, timeout=0):
        self.redis.lpush(self.redis_channel_requests, json.dumps({'function': self.function, 'euuid': self.euuid, 'replyto': self.redis_channel_replies, 'args': {**self.args}}))
        t = time.time()
        while True:
            await asyncio.sleep(self.sleep)
            data = self.redis.lpop(self.redis_channel_replies)
            if data is not None:
                try:
                    data = json.loads(data)
                    _, result, euuid, scheme = data.get('function'), data.get('result'), data.get('euuid'), data.get('scheme')
                    if result and euuid==self.euuid:
                        if scheme=='async':
                            yield result
                        else:
                            yield result
                except Exception as e:
                    logging.exception(e)
                if repeat:
                    if not any(isinstance(repeat, cls) for cls in [bool, int]):
                        continue
                    self.redis.lpush(self.redis_channel_requests, json.dumps({'function': self.function, 'euuid': self.euuid, 'replyto': self.redis_channel_replies, 'args': {**self.args}}))
                    if isinstance(repeat, int):
                        repeat -= 1
                        t = time.time()
            elif timeout:
                if time.time()-t > timeout:
                    break 
        return
            
class Serializer:
    def __init__(self):
        pass
    def __call__(self, obj):
        if isinstance(obj, ollama.ListResponse):
            return obj.model_dump_json()
        raise Exception(f"no serializer found for {type(obj)}")

class EventDrivenReactor:
    def __init__(self, *, redis_host, redis_client, redis_password, redis_channel_requests: str, sleep: float = 0.001, **kwargs):
        self.redis_channel_requests = redis_channel_requests
        self.sleep = max(sleep, 0.001)

        self.redis = mop.clients.Redis(
                host=redis_host, 
                client_name=redis_client,
                password=redis_password
        )
        self.serializer = Serializer()
    async def __push__(self, replyto: str, payload: dict):
        try:
            serialized = json.dumps(payload)
            self.redis.lpush(replyto, serialized)
        except Exception:
            logging.exception("Failed to push result to redis")
    async def __run__(self, functor_name: str, replyto: str, euuid, **kwargs):
        func = getattr(self, functor_name)
        try:
            if inspect.isasyncgenfunction(func):
                agen = func(**kwargs)
                async for value in agen:
                    await self.__push__(
                        replyto,
                        {
                            "euuid": euuid,
                            "function": functor_name,
                            "scheme": "async",
                            "result": self.serializer(value),
                            "timestamp": datetime.datetime.now().isoformat(),
                        },
                    )
            elif inspect.iscoroutinefunction(func):
                value = await func(**kwargs)
                await self.__push__(
                    replyto,
                    {
                        "euuid": euuid,
                        "function": functor_name,
                        "scheme": "sync",
                            "result": self.serializer(value),
                        "timestamp": datetime.datetime.now().isoformat(),
                    },
                )
            elif inspect.isgeneratorfunction(func):
                for value in func(**kwargs):
                    await self.__push__(
                        replyto,
                        {
                            "euuid": euuid,
                            "function": functor_name,
                            "scheme": "async",
                            "result": self.serializer(value),
                            "timestamp": datetime.datetime.now().isoformat(),
                        },
                    )
            else:
                loop = asyncio.get_running_loop()
                bound = functools.partial(func, **kwargs)
                value = await loop.run_in_executor(None, bound)
                await self.__push__(
                    replyto,
                    {
                        "euuid": euuid,
                        "function": functor_name,
                        "scheme": "sync",
                        "result": self.serializer(value),
                        "timestamp": datetime.datetime.now().isoformat(),
                    },
                )
        except Exception:
            logging.exception("Error while running EventDrivenReactor function %s", functor_name)
    async def event_driven_loop(self):
        while True:
            await asyncio.sleep(self.sleep)
            try:
                for channel in self.redis.scan_iter(f"{self.redis_channel_requests}:*"):
                    channel = channel.decode() if isinstance(channel, bytes) else channel
                    raw = self.redis.lpop(channel)
                    if raw is None:
                        continue
                    if isinstance(raw, (bytes, bytearray)):
                        raw = raw.decode()
                    try:
                        data = json.loads(raw)
                    except Exception:
                        logging.exception("Invalid JSON from redis: %r", raw)
                        continue
                    function = data.get("function")
                    args = data.get("args") or {}
                    replyto = data.get("replyto")
                    euuid = data.get("euuid")
                    if function is None or replyto is None or euuid is None:
                        logging.warning("Missing 'function' or 'replyto' in request: %s", data)
                        continue
                    if not isinstance(function, str) or not isinstance(args, dict):
                        logging.warning("Bad types for 'function' or 'args': %s", data)
                        continue
                    if not hasattr(self, function) or not callable(getattr(self, function)):
                        logging.warning("Unknown or non-callable function requested: %s", function)
                        continue
                    asyncio.create_task(self.__run__(function, replyto, euuid, **args))
            except asyncio.CancelledError:
                logging.exception("Cancelled EventDrivenReactor loop")
            except Exception:
                logging.exception("Unexpected error in EventDrivenReactor loop")

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