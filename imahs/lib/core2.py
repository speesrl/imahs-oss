"""

"""

import uuid
import json
import redis
import ollama
import logging
import asyncio
import inspect
import datetime
import functools

# Event-Driven Reactive Architecture (EDA) with an Actor Model:

class EventDrivingActor:
    def __init__(self, *, redis_host, redis_client, redis_password, redis_target_channel, redis_replyto_channel, function, args, sleep=.1):
        self.redis_replyto_channel = redis_replyto_channel
        self.function = function
        self.euuid = uuid.uuid4().hex
        self.sleep = max(sleep, .1)
        logging.debug(
            f"redis stuff EventDrivingActor {json.dumps([redis_host, redis_client, redis_password])}"
        )
        self.redis = redis.Redis(
                host=redis_host, 
                port=6379,
                decode_responses=True,
                client_name=redis_client,
                password=redis_password
        )
        logging.debug(f"debugging redis_target_channel: {redis_target_channel} redis_replyto_channel: {self.redis_replyto_channel}")
        self.redis.lpush(redis_target_channel, json.dumps({'function': self.function, 'euuid': self.euuid, 'replyto': redis_replyto_channel, 'args': {**args}}))
        logging.debug(f"2")
    async def __call__(self):
        while True:
            await asyncio.sleep(self.sleep)
            data = self.redis.rpop(self.redis_replyto_channel)
            logging.debug(f"debugging channel: {self.redis_replyto_channel}, data: {data}")
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


class EventDrivenReactor:
    def __init__(self, *, redis_host, redis_client, redis_password, redis_channel: str, sleep: float = 0.1, **kwargs):
        self.channel = redis_channel
        self.sleep = max(sleep, 0.1)
        logging.debug(
            f"redis stuff EventDrivenReactor {json.dumps([redis_host, redis_client, redis_password, redis_channel])}"
        )
        self.redis = redis.Redis(
                host=redis_host, 
                port=6379,
                decode_responses=True,
                client_name=redis_client,
                password=redis_password,
                socket_timeout=3
        )
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
                            "result": value,
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
                        "result": value,
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
                            "result": value,
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
                        "result": value,
                        "timestamp": datetime.datetime.now().isoformat(),
                    },
                )
        except Exception:
            logging.exception("Error while running EventDrivenReactor function %s", functor_name)
    async def event_driven_loop(self):
        while True:
            logging.info(f"debugging event_driven_loop: redis channel {self.channel}, sleep {self.sleep}")
            await asyncio.sleep(self.sleep)
            try:
                logging.debug("0")
                raw = self.redis.rpop(self.channel)
                logging.debug("1")
                if raw is None:
                    continue
                logging.debug("2")
                if isinstance(raw, (bytes, bytearray)):
                    raw = raw.decode()
                logging.debug("3")
                try:
                    data = json.loads(raw)
                except Exception:
                    logging.exception("Invalid JSON from redis: %r", raw)
                    continue
                logging.debug("4")
                function = data.get("function")
                args = data.get("args") or {}
                replyto = data.get("replyto")
                euuid = data.get("euuid")
                logging.debug("5")
                if function is None or replyto is None or euuid is None:
                    logging.warning("Missing 'function' or 'replyto' in request: %s", data)
                    continue
                logging.debug("6")
                if not isinstance(function, str) or not isinstance(args, dict):
                    logging.warning("Bad types for 'function' or 'args': %s", data)
                    continue
                logging.debug("7")
                if not hasattr(self, function) or not callable(getattr(self, function)):
                    logging.warning("Unknown or non-callable function requested: %s", function)
                    continue
                logging.debug("8")
                asyncio.create_task(self.__run__(function, replyto, euuid, **args))
            except asyncio.CancelledError:
                logging.exception("Cancelled EventDrivenReactor loop")
            except Exception:
                logging.exception("Unexpected error in EventDrivenReactor loop")

class Ollama(EventDrivenReactor, ollama.Client):
    def __init__(self, *, redis_host, redis_client, redis_password, redis_channel: str, sleep: float = 0.1, host : str = 'https://localhost:11434', **kwargs):
        super().__init__(
            redis_host=redis_host, 
            redis_client=redis_client, 
            redis_password=redis_password, 
            redis_channel=redis_channel, 
            sleep=sleep, 
            host=host, 
            **kwargs
        )